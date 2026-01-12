# Justfile for fileidentification installation
# Provides convenient shortcuts

# Default recipe - show available commands
default:
    @just --list

# get latest version from git and reset
gitreset: 
    git fetch
    git reset --hard HEAD
    git merge '@{u}'
    @echo "reset to latest git version"

# create docker image and entry script
dockerise:
    docker build -t fileidentification .
    @if [ ! -d $HOME/.local/bin ]; then mkdir -p $HOME/.local/bin && echo "export PATH=\"${HOME}/.local/bin:\$PATH\"" | tee -a $HOME/.{bash,zsh}rc ; fi
    chmod +x ./fidr.sh
    @if [ ! -L $HOME/.local/bin/fidr ]; then ln -s `pwd`/fidr.sh $HOME/.local/bin/fidr ; fi
    @echo "created docker image, added fidr to path"

# move custom policies
movepolicies:
    mv -f custom_policies/dasch_policies.json fileidentification/definitions/default_policies.json
    
# dasch docker installation
dasch: gitreset movepolicies dockerise

# Update dependencies
update:
    uv lock --upgrade

# Run type checking with mypy (if configured)
typecheck:
    uv run mypy .

# Format code with ruff
format:
    uv run ruff format .

# Lint code with ruff
lint:
    uv run ruff check .

# Lint and fix issues automatically
lint-fix:
    uv run ruff check --fix .

# Run all checks: lint and typecheck
check: lint typecheck
