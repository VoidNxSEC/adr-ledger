package adr.validation

import rego.v1

default result := {"deny": [], "warn": [], "notes": []}

result := {
  "deny": sort([msg | msg := deny[_]]),
  "warn": sort([msg | msg := warn[_]]),
  "notes": sort([msg | msg := note[_]]),
}

warn contains msg if {
  input.status == "accepted"
  governance := object.get(input, "governance", {})
  governance.classification == "critical"
  required := {"architect", "security_lead"}
  provided := {role | role := object.get(governance, "requires_approval_from", [])[_]}
  missing := required - provided
  count(missing) > 0
  msg := sprintf("%s: accepted critical ADR is missing required approval roles %v", [input.id, sort([role | role := missing[_]])])
}

deny contains msg if {
  delivery := object.get(input, "delivery", {})
  delivery.status == "completed"
  count(object.get(delivery, "evidence", [])) == 0
  msg := sprintf("%s: delivery.status=completed requires at least one evidence entry", [input.id])
}

deny contains msg if {
  delivery := object.get(input, "delivery", {})
  delivery.status == "completed"
  object.get(delivery, "completed_at", "") == ""
  msg := sprintf("%s: delivery.status=completed requires delivery.completed_at", [input.id])
}

warn contains msg if {
  scope := object.get(input, "scope", {})
  envs := object.get(scope, "environments", [])
  envs[_] == "production"
  governance := object.get(input, "governance", {})
  object.get(governance, "review_deadline", "") == ""
  msg := sprintf("%s: production-scoped ADRs require governance.review_deadline", [input.id])
}

warn contains msg if {
  input._meta.has_placeholders
  msg := sprintf("%s: template placeholders are still present", [input.id])
}

warn contains msg if {
  delivery := object.get(input, "delivery", {})
  delivery.status == "blocked"
  object.get(delivery, "notes", "") == ""
  msg := sprintf("%s: blocked delivery should include delivery.notes", [input.id])
}

warn contains msg if {
  delivery := object.get(input, "delivery", {})
  delivery.status == "deferred"
  object.get(delivery, "notes", "") == ""
  msg := sprintf("%s: deferred delivery should include delivery.notes", [input.id])
}

note contains msg if {
  input.status == "proposed"
  msg := sprintf("%s: proposed ADR passed policy gate", [input.id])
}
