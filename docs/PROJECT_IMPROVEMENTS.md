# Melhorias: ADR-Ledger & SecureLLM-MCP

**Data:** 2026-02-05
**Autor:** Claude Sonnet 4.5
**Tipo:** Análise de Melhorias Independentes

---

## Overview

Este documento identifica melhorias para cada projeto independentemente da integração entre eles. São otimizações, novos recursos e refinamentos que aumentam o valor de cada sistema isoladamente.

---

## ADR-Ledger: Melhorias

### 1. MCP Server Nativo -- Priority: Critical

**Problema:**
ADR-Ledger atualmente e apenas CLI + Git repository. Não  há interface programática para AI agents consultarem ADRs em tempo real.

**Solução:**
Criar um MCP server nativo dentro do adr-ledger.

**Implementação:**

```typescript
// adr-ledger/packages/mcp-server/src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

// Wrapper para adr CLI
async function runADRCommand(args: string[]): Promise<string> {
  const cmd = `adr ${args.join(" ")}`;
  const { stdout } = await execAsync(cmd);
  return stdout;
}

// MCP Server
const server = new Server(
  {
    name: "adr-ledger-server",
    version: "1.0.0"
  },
  {
    capabilities: {
      tools: {},
      resources: {}
    }
  }
);

// Tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "adr_list",
      description: "List all ADRs with optional filters",
      inputSchema: {
        type: "object",
        properties: {
          status: { type: "string", enum: ["proposed", "accepted", "rejected", "superseded"] },
          project: { type: "string" },
          classification: { type: "string" }
        }
      }
    },
    {
      name: "adr_show",
      description: "Show full details of a specific ADR",
      inputSchema: {
        type: "object",
        properties: {
          adr_id: { type: "string", description: "ADR ID (e.g., ADR-0042)" }
        },
        required: ["adr_id"]
      }
    },
    {
      name: "adr_search",
      description: "Full-text search across all ADRs",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string" },
          fields: { type: "array", items: { type: "string" }, default: ["context", "decision", "title"] }
        },
        required: ["query"]
      }
    },
    {
      name: "adr_graph",
      description: "Get knowledge graph of ADR relations",
      inputSchema: {
        type: "object",
        properties: {
          adr_id: { type: "string", description: "Optional: center graph on specific ADR" },
          depth: { type: "number", default: 2 }
        }
      }
    }
  ]
}));

// Resources
server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: [
    {
      uri: "adr://all",
      name: "All ADRs (JSON)",
      mimeType: "application/json"
    },
    {
      uri: "adr://accepted",
      name: "Accepted ADRs",
      mimeType: "application/json"
    },
    {
      uri: "adr://graph",
      name: "Knowledge Graph",
      mimeType: "application/json"
    },
    {
      uri: "adr://governance",
      name: "Governance Rules",
      mimeType: "application/yaml"
    }
  ]
}));

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

**Uso:**

```json
// Claude Desktop config
{
  "mcpServers": {
    "adr-ledger": {
      "command": "node",
      "args": ["/path/to/adr-ledger/build/mcp-server/index.js"],
      "env": {
        "ADR_LEDGER_ROOT": "/path/to/adr-ledger"
      }
    }
  }
}
```

**Beneficios:**
- AI agents podem consultar ADRs diretamente
- Real-time access sem export manual
- Integra nativamente com Claude Desktop/Cline
- Base para futuras features (notifications, webhooks)

---

### 2. ADR Templates & Wizards -- Priority: High

**Problema:**
Criar ADRs manualmente e tedioso. Muitos campos repetitivos e estrutura complexa.

**Solução:**
Templates inteligentes por tipo de decisão + wizard interativo.

**Implementação:**

```bash
# adr-ledger/templates/
├── infrastructure.yaml       # Infra decisions (NixOS, Docker, K8s)
├── data-architecture.yaml    # Database, caching, storage
├── security.yaml             # Auth, encryption, compliance
├── api-design.yaml           # REST, GraphQL, protocols
├── library-choice.yaml       # Language libraries, frameworks
└── breaking-change.yaml      # Deprecations, migrations

# Uso
$ adr new --template infrastructure

ADR Wizard: Infrastructure Decision

Basic Information
  Title: Migrate to NixOS-based Infrastructure
  Classification: [1] Critical  [2] Major  [3] Minor  [4] Patch
  Choice: 1

  Projects (comma-separated): CEREBRO, PHANTOM, SPECTRE
  Environments: [1] All  [2] Production only  [3] Staging + Prod  [4] Custom
  Choice: 1

Decision Context
  What problem are you solving?
  > Current infrastructure is not reproducible. Deploy inconsistencies cause bugs.

  What's the current state?
  > Using Docker Compose with manual configuration management.

  Why is this decision needed now?
  > Recent production incident due to config drift. Need reproducibility.

Options Analysis
  Option 1: NixOS (your choice)
  Pros:
    - Declarative configuration
    - Atomic rollbacks
    - Reproducible builds
  Cons:
    - Learning curve
    - Smaller community than Docker

  Option 2: Alternative considered?
  > Kubernetes with Helm
  Why rejected?
  > Overkill for current scale. Higher operational complexity.

  Add another alternative? [y/N] n

Risks & Mitigations
  Risk 1: Team learning curve for NixOS
  Probability: [1] Low  [2] Medium  [3] High
  Choice: 2
  Impact: [1] Low  [2] Medium  [3] High
  Choice: 2
  Mitigation: Provide training + documentation + gradual migration

  Add another risk? [y/N] n

Research & Validation
  Run research_agent to validate decision? [Y/n] y

  Searching: "NixOS vs Docker for infrastructure management"
  Found 8 sources (avg credibility: 0.82)
  Official NixOS documentation found
  No major cons identified in research

  Include research in ADR? [Y/n] y

Governance
  Classification: Critical
  Required Approvers: architect, security_lead
  Compliance Tags: INFRASTRUCTURE

  Review Deadline: 7 days from creation
  Fast-track? [y/N] n

ADR Created: ADR-0051

  File: adr/proposed/ADR-0051.md
  Status: proposed
  Required approvals: 2 (architect, security_lead)

  Next steps:
  1. Review generated ADR: adr show ADR-0051
  2. Edit if needed: vim adr/proposed/ADR-0051.md
  3. Commit: git add adr/proposed/ADR-0051.md && git commit
  4. Request review: gh pr create
```

**Templates:**

```yaml
# templates/infrastructure.yaml
metadata:
  name: "Infrastructure Decision"
  description: "For decisions about deployment, hosting, CI/CD, infrastructure tooling"
  classification_default: "major"
  compliance_tags_default: ["INFRASTRUCTURE"]

sections:
  context:
    prompts:
      - "What problem are you solving?"
      - "What's the current infrastructure setup?"
      - "Why is this decision needed now?"
      - "What constraints exist (cost, time, team skills)?"

  decision:
    prompts:
      - "What infrastructure solution did you choose?"
      - "What's the target architecture?"
      - "How will it be deployed?"

  alternatives:
    min_options: 2
    prompts:
      - "What other infrastructure options did you consider?"
      - "Why were they rejected?"

  implementation:
    required_fields:
      - timeline
      - migration_strategy
      - rollback_plan
    prompts:
      - "What's the migration timeline?"
      - "How will you migrate existing systems?"
      - "What's the rollback plan if something fails?"

  risks:
    min_risks: 1
    common_risks:
      - "Team learning curve"
      - "Migration downtime"
      - "Cost overrun"
      - "Performance degradation"

validation:
  required_sections: [context, decision, alternatives, implementation, risks]
  min_consequences_positive: 2
  min_consequences_negative: 1
```

---

### 3. ADR Changelog Automatico -- Priority: Medium

**Problema:**
Quando ADRs são atualizados, não  há histórico estruturado de mudanças.

**Solução:**
Git hooks que geram changelog automático na frontmatter.

```yaml
---
id: "ADR-0042"
title: "Add Redis for API Caching"
status: accepted
date: "2026-01-15"

changelog:
  - date: "2026-01-15"
    author: "pina"
    commit: "a1b2c3d4"
    change: "Initial proposal"

  - date: "2026-01-17"
    author: "maria"
    commit: "e5f6g7h8"
    change: "Added disaster recovery section"
    reviewer: true

  - date: "2026-01-20"
    author: "pina"
    commit: "i9j0k1l2"
    change: "Status: proposed -> accepted"
    approvals:
      - role: "architect"
        name: "pina"
      - role: "security_lead"
        name: "maria"
---
```

**Git Hook:**

```bash
#!/bin/bash
# .git/hooks/post-commit

# Detect modified ADRs
MODIFIED_ADRS=$(git diff HEAD~1 --name-only | grep 'adr/.*\.md')

for adr in $MODIFIED_ADRS; do
  # Extract current changelog
  # Append new entry
  # Update file

  python3 <<EOF
import yaml
import re
from datetime import datetime

with open('$adr') as f:
    content = f.read()

# Extract frontmatter
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
data = yaml.safe_load(match.group(1))

# Get commit info
commit_hash = "$(git rev-parse --short HEAD)"
author = "$(git log -1 --format='%an')"
commit_msg = "$(git log -1 --format='%s')"

# Append changelog entry
if 'changelog' not in data:
    data['changelog'] = []

data['changelog'].append({
    'date': datetime.now().isoformat().split('T')[0],
    'author': author,
    'commit': commit_hash,
    'change': commit_msg
})

# Rewrite file
new_frontmatter = yaml.dump(data, sort_keys=False)
new_content = f"---\n{new_frontmatter}---\n\n" + content.split('---', 2)[2]

with open('$adr', 'w') as f:
    f.write(new_content)
EOF
done
```

---

### 4. Visual Knowledge Graph -- Priority: Medium

**Problema:**
Relacoes entre ADRs (supersedes, enables, related) são dificeis de visualizar.

**Solução:**
Gerar grafo interativo (D3.js) das relacoes.

```bash
$ adr graph --output graph.html

# Gera visualização interativa
```

**Implementação:**

```typescript
// adr-ledger/scripts/generate-graph.ts
import { readFileSync, writeFileSync } from "fs";
import { parse } from "./adr-parser";

interface GraphNode {
  id: string;
  title: string;
  status: string;
  classification: string;
  projects: string[];
}

interface GraphEdge {
  source: string;
  target: string;
  type: "supersedes" | "enables" | "related" | "implements";
}

async function generateGraph() {
  const adrs = await parse("adr/");

  const nodes: GraphNode[] = adrs.map(adr => ({
    id: adr.id,
    title: adr.title,
    status: adr.status,
    classification: adr.classification,
    projects: adr.projects
  }));

  const edges: GraphEdge[] = [];

  for (const adr of adrs) {
    for (const target of adr.supersedes) {
      edges.push({ source: adr.id, target, type: "supersedes" });
    }
    for (const target of adr.enables) {
      edges.push({ source: adr.id, target, type: "enables" });
    }
    for (const target of adr.related_to) {
      edges.push({ source: adr.id, target, type: "related" });
    }
  }

  // Generate D3.js HTML
  const html = generateD3Visualization(nodes, edges);

  writeFileSync("graph.html", html);
  console.log("Graph generated: graph.html");
}

function generateD3Visualization(nodes: GraphNode[], edges: GraphEdge[]): string {
  return `
<!DOCTYPE html>
<html>
<head>
  <title>ADR Knowledge Graph</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; }
    svg { border: 1px solid #ccc; }

    .node circle {
      stroke: #fff;
      stroke-width: 2px;
    }

    .node.accepted circle { fill: #28a745; }
    .node.proposed circle { fill: #ffc107; }
    .node.rejected circle { fill: #dc3545; }
    .node.superseded circle { fill: #6c757d; }

    .link {
      stroke: #999;
      stroke-opacity: 0.6;
    }

    .link.supersedes { stroke: #dc3545; stroke-dasharray: 5,5; }
    .link.enables { stroke: #28a745; }
    .link.related { stroke: #007bff; }

    .label {
      font-size: 12px;
      pointer-events: none;
    }

    .tooltip {
      position: absolute;
      background: white;
      border: 1px solid #ddd;
      padding: 10px;
      border-radius: 4px;
      pointer-events: none;
      display: none;
    }
  </style>
</head>
<body>
  <div id="graph"></div>
  <div class="tooltip" id="tooltip"></div>

  <script>
    const nodes = ${JSON.stringify(nodes)};
    const edges = ${JSON.stringify(edges)};

    const width = window.innerWidth;
    const height = window.innerHeight;

    const svg = d3.select("#graph")
      .append("svg")
      .attr("width", width)
      .attr("height", height);

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id(d => d.id).distance(150))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
      .selectAll("line")
      .data(edges)
      .enter().append("line")
      .attr("class", d => \`link \${d.type}\`)
      .attr("stroke-width", 2);

    const node = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .enter().append("g")
      .attr("class", d => \`node \${d.status}\`)
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    node.append("circle")
      .attr("r", 10);

    node.append("text")
      .attr("class", "label")
      .attr("dx", 15)
      .attr("dy", 5)
      .text(d => d.id);

    node.on("mouseover", function(event, d) {
      d3.select("#tooltip")
        .style("display", "block")
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY + 10) + "px")
        .html(\`
          <strong>\${d.id}</strong><br>
          \${d.title}<br>
          Status: \${d.status}<br>
          Classification: \${d.classification}<br>
          Projects: \${d.projects.join(", ")}
        \`);
    });

    node.on("mouseout", function() {
      d3.select("#tooltip").style("display", "none");
    });

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node.attr("transform", d => \`translate(\${d.x},\${d.y})\`);
    });

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  </script>
</body>
</html>
  `;
}
```

---

### 5. ADR Diffing & Comparison -- Priority: Low

**Problema:**
Comparar duas versoes de ADR ou duas ADRs relacionadas e manual.

**Solução:**
Tool de diff semantico.

```bash
# Compare two ADR versions
$ adr diff ADR-0042 --from HEAD~3 --to HEAD

# Compare two related ADRs
$ adr compare ADR-0012 ADR-0042

# Output
ADR Comparison: ADR-0012 vs ADR-0042

Status:
  ADR-0012: superseded (by ADR-0042)
  ADR-0042: accepted

Decision Evolution:
  ADR-0012: "Use in-memory caching"
  ADR-0042: "Use Redis for distributed caching"

  -> Decision shifted from local to distributed caching

Key Changes:
  + Redis enables horizontal scaling
  + Persistent caching (survives restarts)
  + Cache sharing across replicas
  - Higher infrastructure cost
  - Additional dependency (Redis server)

Governance:
  ADR-0012: minor
  ADR-0042: major (upgraded due to infrastructure impact)

Relations:
  ADR-0042 supersedes ADR-0012
  ADR-0042 enables ADR-0045 (Rate Limiting with Redis)
```

---

## SecureLLM-MCP: Melhorias

### 6. Smart Caching Layer v2 -- Priority: High

**Problema:**
Semantic cache atual e baseado em embeddings 1:1. Pode ser melhorado com clustering e hierarchical caching.

**Solução:**
Cache hierarquico com clustering automático.

```typescript
interface CacheHierarchy {
  // L1: Exact match cache (hash-based, instant)
  l1: Map<string, CachedResult>;

  // L2: Semantic similarity cache (embeddings, <10ms)
  l2: SemanticCache;

  // L3: Cluster cache (query clusters, <50ms)
  l3: ClusterCache;

  // L4: LLM-powered cache (rewrite query, <200ms)
  l4: LLMCache;
}

class SmartCacheV2 {
  async get(query: string, threshold = 0.85): Promise<CachedResult | null> {
    // L1: Exact hash match
    const hash = hashQuery(query);
    if (this.l1.has(hash)) {
      metrics.increment("cache.l1.hit");
      return this.l1.get(hash)!;
    }

    // L2: Semantic similarity (current implementation)
    const semantic = await this.l2.search(query, threshold);
    if (semantic) {
      metrics.increment("cache.l2.hit");
      return semantic;
    }

    // L3: Cluster-based cache
    const cluster = await this.l3.findCluster(query);
    if (cluster && cluster.confidence > 0.7) {
      metrics.increment("cache.l3.hit");
      return cluster.representative_result;
    }

    // L4: LLM query rewriting
    if (this.l4.enabled) {
      const rewritten = await this.l4.rewriteQuery(query);
      if (rewritten.confidence > 0.8) {
        const result = await this.l2.search(rewritten.query, threshold);
        if (result) {
          metrics.increment("cache.l4.hit");
          return result;
        }
      }
    }

    metrics.increment("cache.miss");
    return null;
  }

  async set(query: string, result: any, ttl?: number) {
    const hash = hashQuery(query);

    // Store in L1
    this.l1.set(hash, { query, result, timestamp: Date.now(), ttl });

    // Store in L2 (with embedding)
    const embedding = await generateEmbedding(query);
    await this.l2.store(query, embedding, result, ttl);

    // Update L3 clusters (async)
    this.l3.addToCluster(query, embedding, result).catch(console.error);
  }
}

// L3: Cluster Cache
class ClusterCache {
  private clusters: QueryCluster[] = [];

  async addToCluster(query: string, embedding: number[], result: any) {
    // Find best cluster
    let bestCluster = this.findBestCluster(embedding);

    if (!bestCluster) {
      // Create new cluster
      bestCluster = {
        id: generateId(),
        centroid: embedding,
        queries: [],
        representative_result: result
      };
      this.clusters.push(bestCluster);
    }

    bestCluster.queries.push({ query, embedding, result });

    // Update centroid
    this.updateCentroid(bestCluster);

    // Choose best representative (most common result)
    this.updateRepresentative(bestCluster);
  }

  findBestCluster(embedding: number[]): QueryCluster | null {
    let best: QueryCluster | null = null;
    let maxSimilarity = 0.6;  // Minimum threshold

    for (const cluster of this.clusters) {
      const similarity = cosineSimilarity(embedding, cluster.centroid);
      if (similarity > maxSimilarity) {
        maxSimilarity = similarity;
        best = cluster;
      }
    }

    return best;
  }

  async findCluster(query: string): Promise<{ representative_result: any; confidence: number } | null> {
    const embedding = await generateEmbedding(query);
    const cluster = this.findBestCluster(embedding);

    if (cluster) {
      const similarity = cosineSimilarity(embedding, cluster.centroid);
      return {
        representative_result: cluster.representative_result,
        confidence: similarity
      };
    }

    return null;
  }
}

// L4: LLM Query Rewriter
class LLMCache {
  enabled = true;

  async rewriteQuery(query: string): Promise<{ query: string; confidence: number }> {
    // Use cheap model (e.g., GPT-4o-mini) to rewrite query
    const prompt = `
Rewrite this query to be more cache-friendly (standard form):

Original: "${query}"

Rules:
1. Remove filler words
2. Standardize phrasing
3. Preserve intent

Rewritten query:
    `;

    const response = await callLLM(prompt, { model: "gpt-4o-mini", max_tokens: 50 });

    const rewritten = response.trim();
    const confidence = calculateConfidence(query, rewritten);

    return { query: rewritten, confidence };
  }
}
```

**Estimated benefits:**
- Cache hit rate: 40% -> estimated 70%
- Avg latency: estimated 50ms -> 15ms (L1/L2 hits)
- Cost reduction: estimated 60% -> 85%

---

### 7. Proactive Insight Extraction -- Priority: High

**Problema:**
Knowledge DB apenas armazena o que usuario explicitamente salva. Muita informação valiosa e perdida.

**Solução:**
Sistema que extrai insights automaticamente de conversas e código.

```typescript
class ProactiveInsightExtractor {
  private patterns = [
    // Decision patterns
    {
      regex: /(?:decided|chose|selected|went with)\s+(.+?)\s+(?:over|instead of)\s+(.+?)(?:\.|because)/i,
      type: "decision",
      extract: (match: RegExpMatchArray) => ({
        decision: match[1],
        alternative: match[2],
        type: "decision"
      })
    },

    // Problem patterns
    {
      regex: /(?:issue|problem|bug|error)\s+(?:with|in)\s+(.+?)\s+(?:is|was|that)\s+(.+)/i,
      type: "insight",
      extract: (match: RegExpMatchArray) => ({
        subject: match[1],
        problem: match[2],
        type: "insight"
      })
    },

    // Learning patterns
    {
      regex: /(?:learned|discovered|found out)\s+that\s+(.+)/i,
      type: "insight",
      extract: (match: RegExpMatchArray) => ({
        insight: match[1],
        type: "insight"
      })
    },

    // Trade-off patterns
    {
      regex: /trade-off\s+between\s+(.+?)\s+and\s+(.+?)(?:\s+is|\s+:|\.)/i,
      type: "decision",
      extract: (match: RegExpMatchArray) => ({
        option_a: match[1],
        option_b: match[2],
        type: "decision"
      })
    }
  ];

  async analyzeConversation(messages: Message[], session_id: string) {
    const insights: ExtractedInsight[] = [];

    for (const message of messages) {
      if (message.role !== "user" && message.role !== "assistant") continue;

      for (const pattern of this.patterns) {
        const matches = message.content.matchAll(new RegExp(pattern.regex, 'gi'));

        for (const match of matches) {
          const extracted = pattern.extract(match);

          insights.push({
            ...extracted,
            source: "conversation",
            session_id,
            message_id: message.id,
            confidence: calculateConfidence(match[0]),
            timestamp: Date.now()
          });
        }
      }
    }

    // Save high-confidence insights
    for (const insight of insights) {
      if (insight.confidence > 0.7) {
        await this.saveInsight(insight, session_id);
      }
    }

    // Notify user about extracted insights
    if (insights.length > 0) {
      await this.notifyUser({
        type: "insights_extracted",
        count: insights.length,
        preview: insights.slice(0, 3)
      });
    }

    return insights;
  }

  async saveInsight(insight: ExtractedInsight, session_id: string) {
    await saveKnowledge({
      session_id,
      type: insight.type,
      content: formatInsight(insight),
      tags: extractTags(insight),
      priority: insight.confidence > 0.9 ? "high" : "medium",
      metadata: {
        auto_extracted: true,
        confidence: insight.confidence,
        source: insight.source,
        message_id: insight.message_id
      }
    });
  }
}

// Background job
setInterval(async () => {
  const recentSessions = await getRecentSessions(24 * 60 * 60 * 1000); // Last 24h

  for (const session of recentSessions) {
    const messages = await getSessionMessages(session.id);
    await extractor.analyzeConversation(messages, session.id);
  }
}, 60 * 60 * 1000); // Run every hour
```

---

### 8. Tool Execution Metrics Dashboard -- Priority: Medium

**Problema:**
Dificil saber quais tools são mais usados, quais falham mais, performance bottlenecks.

**Solução:**
Dashboard web com métricas detalhadas.

```typescript
// Metrics collection (already exists, enhance it)
class ToolMetricsCollector {
  async recordExecution(tool: string, duration: number, success: boolean, error?: string) {
    await db.run(`
      INSERT INTO tool_metrics (tool, duration_ms, success, error, timestamp)
      VALUES (?, ?, ?, ?, ?)
    `, [tool, duration, success ? 1 : 0, error || null, Date.now()]);

    // Update Prometheus
    metrics.histogram("tool_execution_duration", duration, { tool });
    metrics.counter("tool_execution_total", 1, { tool, success: success ? "true" : "false" });

    if (!success) {
      metrics.counter("tool_execution_errors", 1, { tool, error: error || "unknown" });
    }
  }

  async getMetrics(period = "24h"): Promise<ToolMetrics> {
    const since = Date.now() - parsePeriod(period);

    const results = await db.all(`
      SELECT
        tool,
        COUNT(*) as executions,
        AVG(duration_ms) as avg_duration,
        MIN(duration_ms) as min_duration,
        MAX(duration_ms) as max_duration,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
        (SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as success_rate
      FROM tool_metrics
      WHERE timestamp > ?
      GROUP BY tool
      ORDER BY executions DESC
    `, [since]);

    return {
      period,
      tools: results,
      total_executions: results.reduce((sum, r) => sum + r.executions, 0),
      avg_success_rate: results.reduce((sum, r) => sum + r.success_rate, 0) / results.length
    };
  }
}

// Web dashboard (Express + React)
app.get("/metrics", async (req, res) => {
  const period = req.query.period || "24h";
  const metrics = await metricsCollector.getMetrics(period);

  res.json(metrics);
});

// HTML dashboard
app.get("/dashboard", (req, res) => {
  res.send(`
<!DOCTYPE html>
<html>
<head>
  <title>SecureLLM MCP Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
    .metric-card {
      border: 1px solid #ddd;
      padding: 20px;
      border-radius: 8px;
      background: white;
    }
    .metric-value { font-size: 32px; font-weight: bold; color: #007bff; }
    .metric-label { color: #666; }
    canvas { max-width: 100%; }
  </style>
</head>
<body>
  <h1>SecureLLM MCP Dashboard</h1>

  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Total Executions (24h)</div>
      <div class="metric-value" id="total-executions">-</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Avg Success Rate</div>
      <div class="metric-value" id="success-rate">-</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Semantic Cache Hit Rate</div>
      <div class="metric-value" id="cache-hit-rate">-</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Knowledge Entries</div>
      <div class="metric-value" id="knowledge-count">-</div>
    </div>
  </div>

  <h2>Tool Usage</h2>
  <canvas id="tool-usage-chart"></canvas>

  <h2>Tool Performance (avg duration)</h2>
  <canvas id="tool-performance-chart"></canvas>

  <script>
    async function loadMetrics() {
      const response = await fetch("/metrics?period=24h");
      const data = await response.json();

      document.getElementById("total-executions").textContent = data.total_executions;
      document.getElementById("success-rate").textContent = data.avg_success_rate.toFixed(1) + "%";

      // Tool usage chart
      new Chart(document.getElementById("tool-usage-chart"), {
        type: "bar",
        data: {
          labels: data.tools.map(t => t.tool),
          datasets: [{
            label: "Executions",
            data: data.tools.map(t => t.executions),
            backgroundColor: "#007bff"
          }]
        }
      });

      // Performance chart
      new Chart(document.getElementById("tool-performance-chart"), {
        type: "bar",
        data: {
          labels: data.tools.map(t => t.tool),
          datasets: [{
            label: "Avg Duration (ms)",
            data: data.tools.map(t => t.avg_duration),
            backgroundColor: "#28a745"
          }]
        }
      });
    }

    loadMetrics();
    setInterval(loadMetrics, 60000); // Refresh every minute
  </script>
</body>
</html>
  `);
});
```

---

### 9. Intelligent Rate Limit Auto-Tuning -- Priority: Medium

**Problema:**
Rate limits são estaticos. Não se adaptam a padroes de uso reais.

**Solução:**
Sistema que ajusta rate limits automaticamente baseado em histórico.

```typescript
class AdaptiveRateLimiter {
  private learningWindow = 7 * 24 * 60 * 60 * 1000; // 7 days

  async analyzeUsagePatterns(provider: string): Promise<UsagePattern> {
    const since = Date.now() - this.learningWindow;

    const hourly = await db.all(`
      SELECT
        strftime('%H', datetime(timestamp/1000, 'unixepoch')) as hour,
        COUNT(*) as requests,
        AVG(duration_ms) as avg_duration
      FROM rate_limiter_events
      WHERE provider = ? AND timestamp > ?
      GROUP BY hour
      ORDER BY hour
    `, [provider, since]);

    // Detect peaks
    const avgRequests = hourly.reduce((sum, h) => sum + h.requests, 0) / hourly.length;
    const peakHours = hourly.filter(h => h.requests > avgRequests * 1.5);

    return {
      provider,
      avg_requests_per_hour: avgRequests,
      peak_hours: peakHours.map(h => parseInt(h.hour)),
      current_limit: this.getLimitConfig(provider),
      recommended_limit: this.calculateOptimalLimit(hourly)
    };
  }

  calculateOptimalLimit(hourly: HourlyStats[]): RateLimit {
    // P95 of hourly requests
    const sorted = hourly.map(h => h.requests).sort((a, b) => a - b);
    const p95 = sorted[Math.floor(sorted.length * 0.95)];

    // Add 20% buffer
    const recommended = Math.ceil(p95 * 1.2);

    // Never go below minimum
    const minimum = 10;

    return {
      requests_per_hour: Math.max(recommended, minimum),
      burst: Math.ceil(recommended / 4),  // 25% burst capacity
      confidence: calculateConfidence(hourly)
    };
  }

  async autoTune(provider: string) {
    const pattern = await this.analyzeUsagePatterns(provider);

    if (pattern.confidence > 0.8) {
      const current = pattern.current_limit;
      const recommended = pattern.recommended_limit;

      if (recommended.requests_per_hour !== current.requests_per_hour) {
        console.log(`Auto-tuning rate limit for ${provider}`);
        console.log(`  Current: ${current.requests_per_hour} req/h`);
        console.log(`  Recommended: ${recommended.requests_per_hour} req/h`);

        await this.updateLimit(provider, recommended);

        await this.notifyUser({
          type: "rate_limit_auto_tuned",
          provider,
          old_limit: current,
          new_limit: recommended,
          reason: `Based on ${this.learningWindow / (24*60*60*1000)} days of usage data`
        });
      }
    }
  }
}

// Background job
setInterval(async () => {
  const providers = ["anthropic", "openai", "deepseek", "gemini"];

  for (const provider of providers) {
    await rateLimiter.autoTune(provider);
  }
}, 24 * 60 * 60 * 1000); // Daily auto-tuning
```

---

### 10. Context-Aware Tool Suggestions -- Priority: Low

**Problema:**
Usuario não sabe quais tools existem ou quando usa-los.

**Solução:**
Sistema que sugere tools baseado em contexto atual.

```typescript
class ToolSuggestionEngine {
  private rules = [
    {
      trigger: "high_cpu_temperature",
      condition: (context) => context.cpu_temp > 75,
      suggestions: [
        "thermal_check",
        "thermal_warroom",
        "force_cooldown"
      ],
      message: "High CPU temperature detected. Consider thermal monitoring."
    },

    {
      trigger: "nix_build_failure",
      condition: (context) => context.last_command?.includes("nix build") && context.last_exit_code !== 0,
      suggestions: [
        "package_diagnose",
        "rebuild_safety_check",
        "research_agent"
      ],
      message: "Nix build failed. Try package_diagnose or research the error."
    },

    {
      trigger: "architectural_discussion",
      condition: (context) => containsArchitecturalKeywords(context.recent_messages),
      suggestions: [
        "adr_create",
        "research_agent",
        "adr_query"
      ],
      message: "Architectural discussion detected. Consider creating an ADR."
    },

    {
      trigger: "code_refactoring",
      condition: (context) => context.files_changed > 10,
      suggestions: [
        "advanced_code_analysis",
        "adr_create",
        "git_commit"
      ],
      message: "Large refactoring detected. Document decision and analyze impact."
    },

    {
      trigger: "repeated_query",
      condition: (context) => context.query_count > 3 && context.unique_queries < 2,
      suggestions: [
        "save_knowledge",
        "create_session"
      ],
      message: "Repeated query detected. Save this as knowledge for future reference."
    }
  ];

  async analyze(context: ExecutionContext): Promise<ToolSuggestion[]> {
    const suggestions: ToolSuggestion[] = [];

    for (const rule of this.rules) {
      if (rule.condition(context)) {
        suggestions.push({
          trigger: rule.trigger,
          tools: rule.suggestions,
          message: rule.message,
          confidence: calculateRuleConfidence(rule, context)
        });
      }
    }

    // Sort by confidence
    return suggestions.sort((a, b) => b.confidence - a.confidence);
  }

  async notifySuggestions(suggestions: ToolSuggestion[]) {
    for (const suggestion of suggestions.slice(0, 2)) { // Top 2
      if (suggestion.confidence > 0.7) {
        await notifyUser({
          type: "tool_suggestion",
          message: suggestion.message,
          tools: suggestion.tools.map(t => ({
            name: t,
            description: getToolDescription(t)
          }))
        });
      }
    }
  }
}

// Hook into tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // ... execute tool ...

  // Analyze context and suggest
  const context = await buildExecutionContext(request);
  const suggestions = await suggestionEngine.analyze(context);

  if (suggestions.length > 0) {
    await suggestionEngine.notifySuggestions(suggestions);
  }

  return result;
});
```

---

## Comparativo: Impacto das Melhorias

| Melhoria | Projeto | Prioridade | Esforço | Impacto |
|----------|---------|------------|---------|---------|
| MCP Server Nativo | ADR-Ledger | Critical | 2 weeks | Alto |
| ADR Templates | ADR-Ledger | High | 1 week | Alto |
| ADR Changelog | ADR-Ledger | Medium | 3 days | Medio |
| Visual Graph | ADR-Ledger | Medium | 1 week | Medio |
| ADR Diffing | ADR-Ledger | Low | 1 week | Baixo |
| Smart Cache v2 | SecureLLM | High | 2 weeks | Alto |
| Insight Extraction | SecureLLM | High | 2 weeks | Alto |
| Metrics Dashboard | SecureLLM | Medium | 1 week | Medio |
| Adaptive Rate Limiting | SecureLLM | Medium | 1 week | Medio |
| Tool Suggestions | SecureLLM | Low | 1 week | Baixo |

---

## Roadmap de Implementação (Independente)

### ADR-Ledger: Q1 2026

**Semana 1-2: MCP Server**
- Criar package `@adr-ledger/mcp-server`
- Implementar tools: list, show, search, graph
- Implementar resources
- Testes + documentação

**Semana 3: Templates**
- Criar templates por categoria
- Wizard interativo CLI
- Validação automática

**Semana 4: Changelog + Polish**
- Git hooks para changelog
- Visual graph (D3.js)
- Diff tool

---

### SecureLLM-MCP: Q1 2026

**Semana 1-2: Smart Cache v2**
- Implementar L3 cluster cache
- Implementar L4 LLM rewriter
- Benchmarks + otimizacao

**Semana 3-4: Proactive Insights**
- Pattern extraction engine
- Background analysis job
- User notifications

**Semana 5: Observability**
- Metrics dashboard (Express + Chart.js)
- Adaptive rate limiting
- Tool suggestions engine

---

## KPIs de Sucesso (estimativas)

### ADR-Ledger

| Métrica | Baseline (estimado) | Target (estimado) | Melhoria estimada |
|---------|---------------------|--------------------|--------------------|
| Time to create ADR | 60 min | 15 min | ~75% |
| ADRs created/month | 2 | 10 | ~5x |
| ADR query time | 15 min | <1 min | ~93% |
| Governance violations | 5/month | 1/month | ~80% |

### SecureLLM-MCP

| Métrica | Baseline (estimado) | Target (estimado) | Melhoria estimada |
|---------|---------------------|--------------------|--------------------|
| Cache hit rate | 40% | 70% | ~75% |
| Avg tool latency | 200ms | 50ms | ~75% |
| Knowledge entries/week | 5 | 20 | ~4x |
| Error rate | 3% | 1% | ~67% |

Nota: estes valores são projeções, não medições. Resultados reais dependerao da implementação e do ambiente de uso.

---

## Conclusão

As melhorias propostas visam elevar ambos os projetos em termos de maturidade:

**ADR-Ledger:** de sistema passivo (Git repo) para plataforma ativa (MCP server), de documentação manual para geração assistida (templates + wizards), de busca linear para navegacao semântica (graph + diff).

**SecureLLM-MCP:** de cache basico para cache hierarquico (clustering), de storage passivo para extração proativa (auto-insights), de caixa-preta para observabilidade (dashboard + metrics).

---

**Autor:** Claude Sonnet 4.5
**Data:** 2026-02-05
**Status:** Proposta em avaliação
