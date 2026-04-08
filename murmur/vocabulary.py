"""
IT managed services domain vocabulary correction.
Uses rapidfuzz for fuzzy matching; KenLM (when available) validates candidates
in context before committing a substitution.
"""
from rapidfuzz import process, fuzz

# Single-word domain terms only — multi-word phrases handled by normalizer regex
_VOCAB = [
    # ITSM frameworks & tools
    "ITIL", "ITSM", "ServiceNow", "Jira", "Confluence", "Remedy", "Zendesk",
    # Incident & change management
    "incident", "escalation", "triage", "workaround", "hotfix", "rollback",
    "SLA", "SLO", "SLI", "MTTR", "MTBF", "CMDB", "runbook",
    # Support tiers
    "helpdesk", "L1", "L2", "L3",
    # Infrastructure & virtualisation
    "hypervisor", "VMware", "vSphere", "vCenter", "Hyper-V", "KVM",
    "Kubernetes", "Docker", "container", "microservice",
    "Azure", "AWS", "GCP", "EC2", "S3",
    # Security
    "LDAP", "SSO", "MFA", "VPN", "endpoint", "firewall", "WAF",
    "SIEM", "SOC", "CVE", "pentest",
    # Monitoring & observability
    "Datadog", "Grafana", "Prometheus", "PagerDuty", "OpsGenie", "APM",
    # Backup & DR
    "failover", "failback", "RTO", "RPO",
    # Networking
    "VLAN", "subnet", "BGP", "OSPF", "latency", "throughput", "bandwidth",
    # Auth & integration
    "OAuth", "SAML", "webhook", "middleware",
    # DevOps
    "deployment", "DevOps", "DevSecOps", "pipeline",
    # General
    "authentication", "authorization", "monitoring", "alerting", "observability",
    "virtualization", "containerization", "orchestration",
    # CLI tools and shell
    "git", "gh", "npm", "npx", "pip", "pip3", "brew", "apt", "yarn", "pnpm",
    "cargo", "gem", "poetry", "conda", "docker", "kubectl", "helm", "terraform",
    "ansible", "pulumi", "python", "python3", "node", "ruby", "rust", "golang",
    "java", "swift", "psql", "mysql", "redis", "mongo", "sqlite", "nginx",
    "systemctl", "journalctl", "ssh", "scp", "curl", "wget", "rsync", "grep",
    "awk", "sed", "vim", "nvim", "tmux", "screen", "jq", "yq", "fzf",
    "GitHub", "GitLab", "Bitbucket", "Homebrew", "PyPI", "crontab",
    "chmod", "chown", "sudo", "bash", "zsh", "fish", "vscode", "heroku",
    "vercel", "netlify", "webpack", "vite", "gcloud",
    # Indian first names
    "Nithin", "Nikhil", "Naveen", "Naresh", "Nandish", "Rahul", "Rajesh",
    "Ramesh", "Rakesh", "Ravi", "Rohan", "Rohit", "Priya", "Priyanka", "Pooja",
    "Arjun", "Arun", "Anand", "Ankit", "Anirudh", "Akshay", "Abhishek", "Aditya",
    "Suresh", "Sanjay", "Santosh", "Satish", "Sunil", "Deepak", "Dinesh",
    "Devesh", "Dhruv", "Kiran", "Kavita", "Kartik", "Kamal", "Mahesh", "Manish",
    "Mukesh", "Mohan", "Vijay", "Vinay", "Vishal", "Vivek", "Shankar", "Shyam",
    "Shreya", "Shweta", "Shubham", "Ganesh", "Girish", "Gaurav", "Amit",
    "Harish", "Hari", "Hemant", "Jayesh", "Jayant", "Lakshmi", "Laxman",
    "Pranav", "Prasad", "Prashanth", "Sachin", "Samir", "Teja", "Tejas",
    "Uday", "Usha", "Vaishnavi", "Varun", "Vasanth", "Yogesh", "Yashwant", "Pavan",
    # Indian surnames
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Nair", "Menon",
    "Pillai", "Rao", "Reddy", "Iyer", "Iyengar", "Agarwal", "Joshi", "Mishra",
    "Tiwari", "Pandey", "Dwivedi", "Chatterjee", "Banerjee", "Mukherjee", "Ghosh",
    "Bose", "Das", "Sen", "Naidu", "Gowda", "Hegde", "Shetty", "Kamath", "Bhat",
    "Pai", "Shah", "Mehta", "Modi", "Desai", "Bhatt", "Trivedi", "Malhotra",
    "Kapoor", "Khanna", "Arora", "Bhatia", "Krishnan", "Subramaniam", "Balakrishnan",
]

# Only substitute if similarity is at or above this threshold
_THRESHOLD = 88


def correct(text: str) -> str:
    """
    Correct domain terminology in text.
    When KenLM is available, a candidate is only applied if it improves the
    sentence-level log-probability; otherwise the best rapidfuzz match wins.
    """
    from murmur import kenlm_rescorer  # lazy to avoid circular import at module load

    words = text.split()
    use_lm = kenlm_rescorer.has_model()
    current_score = kenlm_rescorer.score(text) if use_lm else 0.0

    result = list(words)
    for i, word in enumerate(words):
        # Skip short tokens and already-matching terms
        if len(word) < 3 or word in _VOCAB:
            continue

        candidates = process.extract(word, _VOCAB, scorer=fuzz.ratio, limit=3)
        eligible = [(w, s) for w, s, _ in candidates if s >= _THRESHOLD and w != word]
        if not eligible:
            continue

        if use_lm:
            # Pick the candidate that most improves the sentence LM score;
            # only substitute if there is a positive log-prob gain.
            best_word, best_delta = word, 0.0
            for candidate, _ in eligible:
                trial = result[:i] + [candidate] + result[i + 1:]
                trial_score = kenlm_rescorer.score(" ".join(trial))
                delta = trial_score - current_score
                if delta > best_delta:
                    best_delta, best_word = delta, candidate
            if best_word != word:
                result[i] = best_word
                current_score += best_delta
        else:
            result[i] = eligible[0][0]

    return " ".join(result)
