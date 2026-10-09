#!/usr/bin/bash
# Mermaid-to-ASCII fallback script
# If Mermaid diagram rendering fails in the Markdown report,
# this script provides an ASCII-art topology fallback.
#
# Usage: bash scripts/mermaid-to-ascii.sh < topology.txt
# Or:    echo "graph TD; A-->B" | bash scripts/mermaid-to-ascii.sh

set -e

if [ -t 0 ]; then
    echo "No input provided. Usage: echo 'graph TD; A-->B' | bash scripts/mermaid-to-ascii.sh"
    echo "Displaying default topology placeholder:"
    echo ""
    echo "    +-------------+"
    echo "    |   Internet  |"
    echo "    +------+------+"
    echo "           |"
    echo "    +------+------+"
    echo "    |   ELB       |"
    echo "    +------+------+"
    echo "           |"
    echo "    +------+------+"
    echo "    |   CCE/ECS   |"
    echo "    +------+------+"
    echo "           |"
    echo "    +------+------+"
    echo "    |  RDS/DCS    |"
    echo "    +-------------+"
    exit 0
fi

INPUT=$(cat)

echo "Mermaid diagram (ASCII fallback):"
echo ""
echo "The following Mermaid diagram could not be rendered:"
echo "$INPUT" | head -5
echo "..."
echo ""
echo "Topology placeholder:"
echo ""
echo "    +-------------+"
echo "    |   Internet  |"
echo "    +------+------+"
echo "           |"
echo "    +------+------+"
echo "    |  Frontend   |"
echo "    +------+------+"
echo "           |"
echo "    +------+------+"
echo "    |  Backend    |"
echo "    +------+------+"
echo "           |"
echo "    +------+------+"
echo "    |  Database   |"
echo "    +-------------+"