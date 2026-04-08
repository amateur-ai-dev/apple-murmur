import logging
from pathlib import Path

import mlx_whisper
import numpy as np

logger = logging.getLogger(__name__)

_MODEL_DIR = Path.home() / ".apple-murmur" / "models"

# Seed vocabulary helps Whisper bias toward CLI/terminal, IT, and Indian names
_INITIAL_PROMPT = (
    # Shell built-ins and file ops
    "bash zsh sh fish chmod chown chgrp sudo su export source alias env printenv "
    "which whereis type echo printf read exec eval trap set unset kill jobs bg fg "
    "nohup disown ulimit umask xargs tee watch ls ll la cd pwd mkdir rmdir rm cp mv "
    "touch ln find locate stat file du df lsof "
    # Text tools
    "cat less more head tail grep egrep fgrep ripgrep rg awk sed cut sort uniq wc "
    "tr diff patch strings hexdump "
    # Version control
    "git gh svn hg git-flow clone commit push pull rebase merge stash diff log "
    "checkout branch tag GitHub GitLab Bitbucket "
    # Package managers
    "npm npx pip pip3 brew apt apt-get yum dnf pacman snap flatpak yarn pnpm cargo "
    "gem poetry conda mamba composer nuget "
    # Containers and infra
    "docker docker-compose kubectl helm k9s kind minikube terraform ansible pulumi "
    "packer vagrant podman buildah skopeo "
    # Languages and runtimes
    "python python3 node nodejs ruby rust java javac golang swift kotlin scala php "
    "perl lua elixir erlang haskell clojure dotnet "
    # Databases
    "psql postgres mysql mysqldump redis-cli mongo mongodump sqlite3 influx clickhouse "
    # Networking
    "ssh scp sftp rsync curl wget httpie nc netcat nmap dig nslookup traceroute ping "
    "ip ifconfig netstat ss tcpdump mtr "
    # Process and system
    "ps top htop btop pkill pgrep strace vmstat iostat sar free uptime uname hostname "
    "dmesg journalctl systemctl launchctl crontab "
    # Editors
    "vim nvim nano emacs vscode helix micro "
    # Build tools
    "make cmake ninja bazel gradle maven ant rake gulp grunt webpack vite rollup esbuild "
    # Cloud CLIs
    "aws gcloud az doctl flyctl vercel netlify heroku railway "
    # Other common tools
    "jq yq fzf bat eza zoxide starship tmux screen direnv dotenv "
    # ITSM and IT ops (retained from v2)
    "ITIL ITSM ServiceNow Jira Confluence incident escalation SLA MTTR CMDB "
    "Kubernetes Azure AWS GCP DevOps CI/CD LDAP SSO MFA VPN Datadog Grafana "
    # Indian first names
    "Nithin Nikhil Naveen Naresh Nandish Rahul Rajesh Ramesh Rakesh Ravi Rohan Rohit "
    "Priya Priyanka Pooja Arjun Arun Anand Ankit Anirudh Akshay Abhishek Aditya "
    "Suresh Sanjay Santosh Satish Sunil Deepak Dinesh Devesh Dhruv Kiran Kavita "
    "Kartik Kamal Mahesh Manish Mukesh Mohan Vijay Vinay Vishal Vivek Shankar Shyam "
    "Shreya Shweta Shubham Ganesh Girish Gaurav Amit Harish Hari Hemant Jayesh "
    "Jayant Lakshmi Laxman Pranav Prasad Prashanth Sachin Samir Teja Tejas Uday "
    "Usha Vaishnavi Varun Vasanth Yogesh Yashwant Pavan "
    # Indian surnames
    "Sharma Verma Gupta Singh Kumar Patel Nair Menon Pillai Rao Reddy Iyer Iyengar "
    "Agarwal Joshi Mishra Tiwari Pandey Dwivedi Chatterjee Banerjee Mukherjee Ghosh "
    "Bose Das Sen Naidu Gowda Hegde Shetty Kamath Bhat Pai Shah Mehta Modi Desai "
    "Bhatt Trivedi Malhotra Kapoor Khanna Arora Bhatia Krishnan Subramaniam Balakrishnan"
)


class Engine:
    def __init__(self, model_name: str = "whisper-tiny-mlx", device=None):  # device unused; MLX auto-selects Neural Engine / GPU
        self.model_name = model_name
        self._model_path = str(_MODEL_DIR / model_name)
        # MLX models lazy-load on first inference call — no explicit load step needed
        logger.info("Engine initialised: model=%s path=%s", model_name, self._model_path)

    def load(self) -> None:
        # No-op for MLX — model is loaded lazily by mlx_whisper on first transcribe call.
        # This method exists so the daemon can call engine.load() without branching.
        logger.info("MLX engine ready (model loads lazily on first transcribe)")

    def transcribe(self, audio: np.ndarray) -> str:
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._model_path,
            temperature=0.0,
            beam_size=3,
            condition_on_previous_text=True,
            initial_prompt=_INITIAL_PROMPT,
        )
        return result["text"].strip()
