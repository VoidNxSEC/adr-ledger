#!/usr/bin/env python3.13
"""ADR Knowledge Graph Renderer

Usage:
  python3.13 scripts/graph_render.py [--format dot|svg|html|all] [--output-dir reports/]
"""

import json
import re
import subprocess
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Color scheme
COLORS = {
    "accepted_ok":       "#90EE90",  # green
    "accepted_lowq":     "#FFD700",  # yellow
    "accepted_unsigned": "#FFA500",  # orange
    "proposed":          "#87CEEB",  # light blue
    "project":           "#D3D3D3",  # grey
}

EDGE_STYLES = {
    "supersedes":  {"color": "#CC0000", "style": "solid",  "label": "supersedes"},
    "related_to":  {"color": "#888888", "style": "dashed", "label": "related"},
    "enables":     {"color": "#008800", "style": "solid",  "label": "enables"},
    "belongs_to":  {"color": "#4444CC", "style": "dotted", "label": ""},
}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data() -> tuple[dict, dict, dict]:
    """Carrega graph.json + chain.json + metrics.json"""
    graph   = json.loads((REPO_ROOT / "knowledge/graph.json").read_text())
    chain   = json.loads((REPO_ROOT / ".chain/chain.json").read_text())
    metrics = json.loads((REPO_ROOT / ".chain/economics/metrics.json").read_text())
    return graph, chain, metrics


def build_chain_overlay(chain: dict, metrics: dict) -> dict[str, dict]:
    """Retorna dict ADR_ID → {block_number, sig_count, low_quality, unsigned}"""
    low_q    = set(metrics["health"]["low_quality_ids"])
    unsigned = set(metrics["health"]["unsigned_ids"])
    overlay  = {}
    for block in chain["chain"]:
        if block["adr_id"] == "GENESIS":
            continue
        adr_id = block["adr_id"]
        overlay[adr_id] = {
            "block_number": block["block_number"],
            "sig_count":    len(block.get("signatures", [])),
            "low_quality":  adr_id in low_q,
            "unsigned":     adr_id in unsigned,
        }
    return overlay


def load_classifications() -> dict[str, str]:
    """Lê classification dos frontmatters das ADRs (accepted + proposed)"""
    result = {}
    for subdir in ["accepted", "proposed"]:
        adr_dir = REPO_ROOT / "adr" / subdir
        if not adr_dir.exists():
            continue
        for md_file in adr_dir.glob("*.md"):
            text = md_file.read_text(errors="replace")
            # Extract id from frontmatter
            id_match = re.search(r'^id:\s*["\']?([A-Z]{3}-\d+)["\']?', text, re.MULTILINE)
            clf_match = re.search(r'^\s+classification:\s*["\']?(\w+)["\']?', text, re.MULTILINE)
            if id_match and clf_match:
                result[id_match.group(1)] = clf_match.group(1)
    return result


def node_color(node: dict, overlay: dict, node_id: str) -> str:
    """Determina a cor do nó baseada em status e qualidade."""
    if node.get("type") == "project":
        return COLORS["project"]
    status = node.get("status", "")
    if status != "accepted":
        return COLORS["proposed"]
    info = overlay.get(node_id, {})
    if info.get("low_quality"):
        return COLORS["accepted_lowq"]
    if info.get("unsigned"):
        return COLORS["accepted_unsigned"]
    return COLORS["accepted_ok"]


def node_label_dot(node: dict, overlay: dict, node_id: str) -> str:
    """Gera label para o DOT (multiline com block + sigs)."""
    if node.get("type") == "project":
        return node.get("label", node_id)
    info = overlay.get(node_id, {})
    if info:
        return f"{node_id}\\n#blk{info['block_number']} sig:{info['sig_count']}"
    return node_id


# =============================================================================
# DOT RENDERER
# =============================================================================

PROJECT_PREFIXES = {
    "CEREBRO": "CEREBRO",
    "SPECTRE": "SPECTRE",
    "PHANTOM": "PHANTOM",
    "NEUTRON": "NEUTRON",
    "GLOBAL":  "GLOBAL",
}


def _dot_node_id(raw_id: str) -> str:
    """Sanitiza o ID para uso no DOT (sem : ou -)."""
    return re.sub(r'[^A-Za-z0-9_]', '_', raw_id)


def render_dot(graph: dict, overlay: dict, classifications: dict, output_path: Path) -> None:
    """Gera arquivo .dot com clusters por projeto."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]

    # Build membership: project_label → [adr_ids]
    project_members: dict[str, list[str]] = {p: [] for p in PROJECT_PREFIXES}
    for node_id, node in nodes.items():
        if node.get("type") == "adr":
            for proj in node.get("projects", []):
                if proj in project_members:
                    project_members[proj].append(node_id)

    project_colors = {
        "CEREBRO": "#E8F4FD",
        "SPECTRE": "#FDF8E8",
        "PHANTOM": "#F4FDE8",
        "NEUTRON": "#FDE8F4",
        "GLOBAL":  "#EDEDED",
    }

    lines = [
        "digraph adr_knowledge_graph {",
        '    graph [rankdir=LR fontname="Helvetica" bgcolor="#FAFAFA" label="ADR Knowledge Graph" fontsize=14 labelloc=t];',
        '    node  [fontname="Helvetica" fontsize=11 style=filled];',
        '    edge  [fontname="Helvetica" fontsize=9];',
        "",
    ]

    # Subgraphs (clusters) por projeto
    rendered_in_cluster: set[str] = set()
    for proj, members in project_members.items():
        if not members:
            continue
        cluster_id = f"cluster_{proj.lower()}"
        color = project_colors.get(proj, "#EEEEEE")
        lines.append(f"    subgraph {cluster_id} {{")
        lines.append(f'        label="{proj}" style=filled fillcolor="{color}" color="#AAAAAA" fontsize=12;')
        for adr_id in sorted(set(members)):
            if adr_id in rendered_in_cluster:
                continue
            rendered_in_cluster.add(adr_id)
            node = nodes[adr_id]
            dot_id = _dot_node_id(adr_id)
            color_fill = node_color(node, overlay, adr_id)
            label = node_label_dot(node, overlay, adr_id)
            clf = classifications.get(adr_id, "major")
            width = {"critical": "1.5", "major": "1.0", "minor": "0.8", "patch": "0.6"}.get(clf, "1.0")
            lines.append(
                f'        {dot_id} [label="{label}" fillcolor="{color_fill}" '
                f'penwidth={width} shape=box];'
            )
        lines.append("    }")
        lines.append("")

    # Nós restantes (não associados a projeto conhecido)
    for node_id, node in nodes.items():
        if node.get("type") == "project":
            dot_id = _dot_node_id(node_id)
            label = node.get("label", node_id)
            lines.append(
                f'    {dot_id} [label="{label}" fillcolor="{COLORS["project"]}" shape=ellipse];'
            )
        elif node_id not in rendered_in_cluster:
            dot_id = _dot_node_id(node_id)
            color_fill = node_color(node, overlay, node_id)
            label = node_label_dot(node, overlay, node_id)
            lines.append(f'    {dot_id} [label="{label}" fillcolor="{color_fill}" shape=box];')

    lines.append("")

    # Edges
    for edge in edges:
        src = _dot_node_id(edge["source"])
        tgt = _dot_node_id(edge["target"])
        etype = edge.get("type", "related_to")
        style = EDGE_STYLES.get(etype, EDGE_STYLES["related_to"])
        attrs = [
            f'color="{style["color"]}"',
            f'style={style["style"]}',
        ]
        if style["label"]:
            attrs.append(f'label="{style["label"]}"')
        if etype == "supersedes":
            attrs.append('penwidth=2 arrowsize=1.2')
        lines.append(f'    {src} -> {tgt} [{" ".join(attrs)}];')

    lines.append("}")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"[dot] Gerado: {output_path}", file=sys.stderr)


# =============================================================================
# SVG RENDERER
# =============================================================================

def render_svg(dot_path: Path, svg_path: Path) -> bool:
    """Chama `dot -Tsvg` para gerar SVG a partir do arquivo DOT."""
    try:
        result = subprocess.run(
            ["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"[svg] ERRO: {result.stderr}", file=sys.stderr)
            return False
        print(f"[svg] Gerado: {svg_path}", file=sys.stderr)
        return True
    except FileNotFoundError:
        print("[svg] AVISO: `dot` não encontrado. Instale graphviz.", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("[svg] ERRO: timeout ao gerar SVG.", file=sys.stderr)
        return False


# =============================================================================
# HTML RENDERER (Cytoscape.js)
# =============================================================================

def _cy_color(node: dict, overlay: dict, node_id: str) -> str:
    return node_color(node, overlay, node_id)


def _cy_size(clf: str) -> int:
    return {"critical": 40, "major": 30, "minor": 20, "patch": 15}.get(clf, 30)


def render_html(graph: dict, overlay: dict, classifications: dict, output_path: Path) -> None:
    """Gera HTML standalone com Cytoscape.js."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]

    # Build Cytoscape elements
    cy_nodes = []
    for node_id, node in nodes.items():
        clf = classifications.get(node_id, "major")
        color = _cy_color(node, overlay, node_id)
        size = _cy_size(clf) if node.get("type") == "adr" else 35
        info = overlay.get(node_id, {})
        short_id = node_id.replace("PROJECT:", "")
        tooltip_parts = [
            f"ID: {node_id}",
            f"Status: {node.get('status', 'N/A')}",
        ]
        if info:
            tooltip_parts += [
                f"Block: #{info['block_number']}",
                f"Assinaturas: {info['sig_count']}",
                f"Quality: {'⚠ baixa' if info['low_quality'] else '✓ ok'}",
                f"Assinado: {'não' if info['unsigned'] else 'sim'}",
            ]
        if clf:
            tooltip_parts.append(f"Classificação: {clf}")
        tooltip = "\\n".join(tooltip_parts)

        label_full = node.get("label", node_id)
        cy_nodes.append({
            "data": {
                "id": node_id,
                "label": short_id,
                "fullLabel": label_full,
                "tooltip": tooltip,
                "color": color,
                "size": size,
                "type": node.get("type", "adr"),
                "status": node.get("status", ""),
                "projects": node.get("projects", []),
                "classification": clf,
                "blockNumber": info.get("block_number", -1),
                "sigCount": info.get("sig_count", 0),
                "lowQuality": info.get("low_quality", False),
                "unsigned": info.get("unsigned", False),
            }
        })

    cy_edges = []
    for i, edge in enumerate(edges):
        etype = edge.get("type", "related_to")
        style = EDGE_STYLES.get(etype, EDGE_STYLES["related_to"])
        cy_edges.append({
            "data": {
                "id": f"e{i}",
                "source": edge["source"],
                "target": edge["target"],
                "type": etype,
                "label": style["label"],
                "color": style["color"],
                "lineStyle": style["style"],
            }
        })

    graph_data = json.dumps({"nodes": cy_nodes, "edges": cy_edges}, indent=2)

    # Build project list for filter dropdown
    all_projects = sorted({
        p for n in nodes.values()
        for p in (n.get("projects") or [])
    })

    project_options = "\n".join(
        f'<option value="{p}">{p}</option>' for p in all_projects
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>ADR Knowledge Graph</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background: #F0F2F5; color: #333; }}
#header {{
    background: #1a1a2e; color: #eee; padding: 10px 16px;
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}}
#header h1 {{ font-size: 1.1rem; flex: 1; }}
#header select, #header button {{
    padding: 5px 10px; border-radius: 4px; border: 1px solid #555;
    background: #2a2a4e; color: #eee; cursor: pointer; font-size: 0.85rem;
}}
#header button:hover {{ background: #3a3a6e; }}
#main {{ display: flex; height: calc(100vh - 46px); }}
#cy {{ flex: 1; background: #fff; }}
#sidebar {{
    width: 280px; background: #fff; border-left: 1px solid #ddd;
    padding: 14px; overflow-y: auto; font-size: 0.85rem;
}}
#sidebar h2 {{ font-size: 1rem; margin-bottom: 10px; color: #1a1a2e; border-bottom: 1px solid #eee; padding-bottom: 6px; }}
#sidebar .field {{ margin-bottom: 6px; }}
#sidebar .field strong {{ display: inline-block; min-width: 80px; color: #555; }}
#sidebar .badge {{
    display: inline-block; padding: 2px 7px; border-radius: 10px;
    font-size: 0.75rem; font-weight: bold;
}}
#footer {{
    background: #1a1a2e; color: #aaa; font-size: 0.75rem;
    padding: 6px 14px; display: flex; gap: 20px; flex-wrap: wrap;
}}
.legend-item {{ display: flex; align-items: center; gap: 5px; }}
.legend-dot {{ width: 12px; height: 12px; border-radius: 2px; border: 1px solid #888; }}
</style>
</head>
<body>

<div id="header">
  <h1>ADR Knowledge Graph</h1>
  <label>Projeto:
    <select id="filterProject">
      <option value="">Todos</option>
      {project_options}
    </select>
  </label>
  <label>Status:
    <select id="filterStatus">
      <option value="">Todos</option>
      <option value="accepted">accepted</option>
      <option value="proposed">proposed</option>
    </select>
  </label>
  <label>Quality:
    <select id="filterQuality">
      <option value="">Todos</option>
      <option value="ok">OK</option>
      <option value="low">Baixa qualidade</option>
      <option value="unsigned">Não assinado</option>
    </select>
  </label>
  <button id="btnReset">Reset</button>
</div>

<div id="main">
  <div id="cy"></div>
  <div id="sidebar">
    <h2>Detalhes</h2>
    <div id="nodeDetails">
      <p style="color:#aaa">Clique em um nó para ver detalhes.</p>
    </div>
  </div>
</div>

<div id="footer">
  <span>Legenda nós:</span>
  <span class="legend-item"><span class="legend-dot" style="background:{COLORS['accepted_ok']}"></span> accepted ok</span>
  <span class="legend-item"><span class="legend-dot" style="background:{COLORS['accepted_lowq']}"></span> baixa qualidade</span>
  <span class="legend-item"><span class="legend-dot" style="background:{COLORS['accepted_unsigned']}"></span> não assinado</span>
  <span class="legend-item"><span class="legend-dot" style="background:{COLORS['proposed']}"></span> proposed</span>
  <span class="legend-item"><span class="legend-dot" style="background:{COLORS['project']}; border-radius:50%"></span> projeto</span>
  &nbsp;|&nbsp;
  <span>Arestas:</span>
  <span class="legend-item"><span style="color:#CC0000">→</span> supersedes</span>
  <span class="legend-item"><span style="color:#888">-→</span> related</span>
  <span class="legend-item"><span style="color:#008800">→</span> enables</span>
  <span class="legend-item"><span style="color:#4444CC">··→</span> belongs_to</span>
</div>

<script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
<script>
const GRAPH_DATA = {graph_data};

const cy = cytoscape({{
  container: document.getElementById('cy'),
  elements: [...GRAPH_DATA.nodes, ...GRAPH_DATA.edges],
  style: [
    {{
      selector: 'node',
      style: {{
        'background-color': 'data(color)',
        'label': 'data(label)',
        'width': 'data(size)',
        'height': 'data(size)',
        'font-size': 10,
        'text-valign': 'center',
        'text-halign': 'center',
        'border-width': 1.5,
        'border-color': '#555',
        'color': '#111',
      }}
    }},
    {{
      selector: 'node[type="project"]',
      style: {{
        'shape': 'ellipse',
        'font-weight': 'bold',
        'font-size': 12,
        'border-width': 2,
        'border-color': '#888',
      }}
    }},
    {{
      selector: 'edge',
      style: {{
        'width': 1.5,
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'line-style': 'data(lineStyle)',
        'label': 'data(label)',
        'font-size': 8,
        'color': '#555',
        'text-background-color': '#fff',
        'text-background-opacity': 0.8,
        'text-background-padding': 2,
      }}
    }},
    {{
      selector: 'edge[type="supersedes"]',
      style: {{ 'width': 2.5, 'font-weight': 'bold' }}
    }},
    {{
      selector: ':selected',
      style: {{
        'border-color': '#FF4444',
        'border-width': 3,
        'line-color': '#FF4444',
        'target-arrow-color': '#FF4444',
      }}
    }},
    {{
      selector: '.faded',
      style: {{ 'opacity': 0.15 }}
    }}
  ],
  layout: {{
    name: 'cose',
    animate: false,
    idealEdgeLength: 120,
    nodeOverlap: 20,
    refresh: 20,
    fit: true,
    padding: 30,
    randomize: false,
    componentSpacing: 80,
    nodeRepulsion: 450000,
    edgeElasticity: 100,
    nestingFactor: 5,
    gravity: 80,
    numIter: 1000,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
  }}
}});

// Sidebar details
const details = document.getElementById('nodeDetails');
cy.on('tap', 'node', function(evt) {{
  const d = evt.target.data();
  let html = '';
  if (d.type === 'project') {{
    html = `<div class="field"><strong>Projeto:</strong> ${{d.label}}</div>`;
  }} else {{
    const qBadge = d.lowQuality
      ? '<span class="badge" style="background:#FFD700">baixa</span>'
      : '<span class="badge" style="background:#90EE90">ok</span>';
    const sigBadge = d.unsigned
      ? '<span class="badge" style="background:#FFA500">não assinado</span>'
      : `<span class="badge" style="background:#90EE90">${{d.sigCount}} sig(s)</span>`;
    const blk = d.blockNumber >= 0 ? `#${{d.blockNumber}}` : 'N/A';
    html = `
      <div class="field"><strong>ID:</strong> ${{d.id}}</div>
      <div class="field"><strong>Bloco:</strong> ${{blk}}</div>
      <div class="field"><strong>Assinaturas:</strong> ${{sigBadge}}</div>
      <div class="field"><strong>Qualidade:</strong> ${{qBadge}}</div>
      <div class="field"><strong>Status:</strong> ${{d.status}}</div>
      <div class="field"><strong>Classif.:</strong> ${{d.classification || 'N/A'}}</div>
      <div class="field" style="margin-top:8px; font-style:italic; color:#555; font-size:0.8rem">${{d.fullLabel}}</div>
    `;
  }}
  details.innerHTML = html;
}});

cy.on('tap', function(evt) {{
  if (evt.target === cy) details.innerHTML = '<p style="color:#aaa">Clique em um nó para ver detalhes.</p>';
}});

// Highlight neighbors on hover
cy.on('mouseover', 'node', function(evt) {{
  const node = evt.target;
  cy.elements().not(node.closedNeighborhood()).addClass('faded');
}});
cy.on('mouseout', 'node', function() {{
  cy.elements().removeClass('faded');
}});

// Filters
function applyFilters() {{
  const proj  = document.getElementById('filterProject').value;
  const stat  = document.getElementById('filterStatus').value;
  const qual  = document.getElementById('filterQuality').value;

  cy.nodes().forEach(n => {{
    const d = n.data();
    if (d.type === 'project') {{ n.style('display', 'element'); return; }}
    let show = true;
    if (proj && !(d.projects || []).includes(proj)) show = false;
    if (stat && d.status !== stat) show = false;
    if (qual === 'ok'       && (d.lowQuality || d.unsigned)) show = false;
    if (qual === 'low'      && !d.lowQuality) show = false;
    if (qual === 'unsigned' && !d.unsigned)   show = false;
    n.style('display', show ? 'element' : 'none');
  }});
  cy.edges().forEach(e => {{
    const src = e.source().style('display') !== 'none';
    const tgt = e.target().style('display') !== 'none';
    e.style('display', src && tgt ? 'element' : 'none');
  }});
}}

document.getElementById('filterProject').addEventListener('change', applyFilters);
document.getElementById('filterStatus').addEventListener('change', applyFilters);
document.getElementById('filterQuality').addEventListener('change', applyFilters);
document.getElementById('btnReset').addEventListener('click', function() {{
  document.getElementById('filterProject').value = '';
  document.getElementById('filterStatus').value  = '';
  document.getElementById('filterQuality').value = '';
  cy.elements().style('display', 'element');
}});
</script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"[html] Gerado: {output_path}", file=sys.stderr)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="ADR Knowledge Graph Renderer")
    parser.add_argument(
        "--format", "-f",
        choices=["dot", "svg", "html", "all"],
        default="all",
        help="Formato de saída (default: all)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="reports",
        help="Diretório de saída (default: reports/)"
    )
    args = parser.parse_args()

    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    graph, chain, metrics = load_data()
    overlay         = build_chain_overlay(chain, metrics)
    classifications = load_classifications()

    fmt = args.format

    dot_path  = output_dir / "knowledge_graph.dot"
    svg_path  = output_dir / "knowledge_graph.svg"
    html_path = output_dir / "knowledge_graph.html"

    if fmt in ("dot", "svg", "all"):
        render_dot(graph, overlay, classifications, dot_path)

    if fmt in ("svg", "all"):
        render_svg(dot_path, svg_path)

    if fmt in ("html", "all"):
        render_html(graph, overlay, classifications, html_path)

    print(f"\nArtefatos gerados em: {output_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
