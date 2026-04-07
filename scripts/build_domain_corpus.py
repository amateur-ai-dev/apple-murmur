#!/usr/bin/env python3
"""
Emits an IT managed services domain corpus to stdout.
Used by install.sh to train the KenLM domain language model:

    python3 build_domain_corpus.py | lmplz -o 3 --discount_fallback > domain.arpa
"""

SENTENCES = [
    # Incident management
    "the incident was escalated to L2 support",
    "please open an incident ticket in ServiceNow",
    "the severity one incident triggered a PagerDuty alert",
    "L1 support could not resolve the issue and escalated to L2",
    "the incident was closed after the workaround was applied",
    "root cause analysis is required for every P1 incident",
    "the post-mortem identified a gap in the runbook",
    "MTTR improved after we automated the incident response",
    "the SLA breach was due to delayed escalation",
    "all incidents must be logged in the CMDB",
    # Change management
    "please submit a change request for the deployment",
    "the change request was approved by the CAB",
    "emergency change requests require VP approval",
    "the rollback plan must be included in the change request",
    "the deployment window is Saturday midnight to Sunday morning",
    "standard changes do not require individual CAB approval",
    "the hotfix was deployed without a formal change request",
    "change management follows ITIL best practices",
    "all changes must have a rollback procedure documented",
    # SLA and performance
    "the SLA target is ninety nine point nine percent uptime",
    "SLO breaches are tracked in the monthly service review",
    "MTBF for the storage array is eighteen months",
    "the RTO for disaster recovery is four hours",
    "the RPO cannot exceed one hour of data loss",
    "SLI metrics are exported to Grafana dashboards",
    # Infrastructure
    "the VMware cluster hosts two hundred virtual machines",
    "we are migrating workloads from on-prem to Azure",
    "the Kubernetes cluster runs on GCP",
    "Docker containers are managed by the DevOps team",
    "the hypervisor upgrade requires a maintenance window",
    "vSphere and vCenter manage the virtualisation layer",
    "Hyper-V is used for the Windows workloads",
    "the EC2 instances are auto-scaled based on CPU utilisation",
    "S3 buckets store backup snapshots for thirty days",
    "the hybrid cloud architecture spans AWS and on-prem data centres",
    "containerization reduced deployment time by sixty percent",
    "Kubernetes orchestration handles pod scheduling automatically",
    # Security
    "Active Directory is the identity provider for all users",
    "SSO is configured via SAML integration with Azure AD",
    "MFA is mandatory for all privileged access",
    "the VPN gateway experienced packet loss during peak hours",
    "endpoint detection and response is managed by the SOC",
    "the WAF blocked three hundred attacks this week",
    "SIEM alerts are reviewed by the security operations team",
    "CVE remediation must be completed within thirty days",
    "patch management covers all endpoints in the estate",
    "the firewall rule change requires a change request",
    "zero trust network access is being rolled out",
    "LDAP integration enables centralised authentication",
    "OAuth tokens expire after one hour",
    "SAML assertions are validated by the identity provider",
    # Monitoring and observability
    "Datadog monitors all production services",
    "Grafana dashboards show real-time infrastructure metrics",
    "Prometheus collects metrics from all microservices",
    "OpsGenie routes alerts to the correct on-call engineer",
    "APM traces identified a slow database query",
    "the alerting threshold was tuned to reduce noise",
    "observability pipelines ingest logs from all environments",
    "the runbook describes how to restart the service",
    # Networking
    "the VLAN was misconfigured causing connectivity issues",
    "subnet allocation is managed by the networking team",
    "BGP route advertisement caused a brief outage",
    "latency between data centres is under five milliseconds",
    "bandwidth utilisation peaked at ninety percent",
    "the load balancer health checks detected a failed node",
    "DNS resolution failures were traced to a misconfigured record",
    "DHCP lease exhaustion caused new devices to fail to connect",
    "SD-WAN provides automatic failover between links",
    # Backup and DR
    "failover to the DR site completed in forty minutes",
    "the failback process is scheduled for the maintenance window",
    "backup jobs are monitored in the backup management portal",
    "disaster recovery tests are conducted quarterly",
    "BCP documentation must be reviewed annually",
    "RPO and RTO targets are defined in the service contract",
    # DevOps and CI/CD
    "the CI/CD pipeline deploys to production on merge",
    "DevOps practices reduced lead time from weeks to hours",
    "DevSecOps integrates security scanning into the pipeline",
    "the deployment pipeline includes automated regression tests",
    "infrastructure as code is managed in the Git repository",
    "the pipeline failed due to a misconfigured webhook",
    # Support tiers
    "helpdesk tickets are triaged within fifteen minutes",
    "L3 support requires vendor escalation for hardware faults",
    "the service desk handles over five hundred tickets per week",
    "first-line support resolved the issue using the knowledge base",
    "escalation to L2 occurs after thirty minutes without resolution",
    # Integration
    "the middleware handles message routing between systems",
    "webhook notifications trigger automated remediation scripts",
    "the API integration between ServiceNow and Jira is bidirectional",
    "ETL pipelines process log data for the analytics platform",
    "the REST API rate limit caused intermittent failures",
    # General
    "the CMDB must reflect the current state of the environment",
    "asset management tracks all hardware and software licences",
    "configuration items are linked to incidents in ServiceNow",
    "the service catalogue lists all IT services and their owners",
    "capacity planning ensures infrastructure can meet demand",
    "the knowledge base article was updated after the incident",
    "problem management identifies and eliminates recurring incidents",
    "the triage call identified the root cause within thirty minutes",
    "the workaround reduced user impact while the fix was developed",
    "release management coordinates deployments across all teams",
]

# Repeat the corpus to give lmplz enough n-gram evidence for smoothing
for _ in range(5):
    for sentence in SENTENCES:
        print(sentence)
