"""
HackBot Network Topology Visualizer
====================================
Parses nmap/masscan scan output into a graph structure of hosts, ports, and services.
Provides JSON data for interactive D3.js visualization in the GUI
and ASCII rendering for CLI.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class TopoNode:
    """A node in the network topology (host, subnet, or service)."""

    id: str
    label: str
    node_type: str  # "scanner", "host", "subnet", "service", "os"
    ip: str = ""
    mac: str = ""
    hostname: str = ""
    os: str = ""
    ports: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "up"  # up, down, filtered
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.node_type,
            "ip": self.ip,
            "mac": self.mac,
            "hostname": self.hostname,
            "os": self.os,
            "ports": self.ports,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class TopoEdge:
    """An edge connecting two nodes in the topology."""

    source: str
    target: str
    edge_type: str = "connection"  # "connection", "scan", "service"
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.edge_type,
            "label": self.label,
            "metadata": self.metadata,
        }


@dataclass
class NetworkTopology:
    """Complete network topology graph."""

    nodes: List[TopoNode] = field(default_factory=list)
    edges: List[TopoEdge] = field(default_factory=list)
    scan_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "scan_info": self.scan_info,
            "timestamp": self.timestamp,
            "stats": {
                "total_hosts": len([n for n in self.nodes if n.node_type == "host"]),
                "total_services": sum(len(n.ports) for n in self.nodes if n.node_type == "host"),
                "subnets": len([n for n in self.nodes if n.node_type == "subnet"]),
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_mermaid(self) -> str:
        return TopologyParser.render_mermaid(self)


# ── Topology Parser ──────────────────────────────────────────────────────────


class TopologyParser:
    """Parse scan output into network topology graphs."""

    def __init__(self, scanner_label: str = "Scanner"):
        self.scanner_label = scanner_label

    def parse_nmap_text(self, output: str) -> NetworkTopology:
        """
        Parse nmap text output into a NetworkTopology.

        Handles standard nmap output format including:
        - Host discovery results
        - Port scan results
        - Service/version detection
        - OS detection
        """
        topo = NetworkTopology()

        # Scanner node (origin)
        scanner = TopoNode(
            id="scanner",
            label=self.scanner_label,
            node_type="scanner",
        )
        topo.nodes.append(scanner)

        # Parse scan info from the header
        scan_info = self._parse_scan_header(output)
        topo.scan_info = scan_info

        # Split output into per-host blocks
        host_blocks = self._split_host_blocks(output)

        subnet_nodes: Dict[str, TopoNode] = {}

        for block in host_blocks:
            host = self._parse_host_block(block)
            if not host:
                continue

            # Determine subnet
            subnet_id = self._get_subnet(host.ip)
            if subnet_id and subnet_id not in subnet_nodes:
                subnet_node = TopoNode(
                    id=f"subnet_{subnet_id}",
                    label=subnet_id,
                    node_type="subnet",
                )
                subnet_nodes[subnet_id] = subnet_node
                topo.nodes.append(subnet_node)

                # Connect scanner to subnet
                topo.edges.append(TopoEdge(
                    source="scanner",
                    target=f"subnet_{subnet_id}",
                    edge_type="scan",
                    label="scanned",
                ))

            topo.nodes.append(host)

            # Connect host to subnet or directly to scanner
            if subnet_id and subnet_id in subnet_nodes:
                topo.edges.append(TopoEdge(
                    source=f"subnet_{subnet_id}",
                    target=host.id,
                    edge_type="connection",
                ))
            else:
                topo.edges.append(TopoEdge(
                    source="scanner",
                    target=host.id,
                    edge_type="scan",
                ))

        return topo

    def parse_nmap_xml(self, xml_content: str) -> NetworkTopology:
        """
        Parse nmap XML output (-oX) into a NetworkTopology.
        XML is the most reliable nmap output format.
        """
        topo = NetworkTopology()

        scanner = TopoNode(
            id="scanner",
            label=self.scanner_label,
            node_type="scanner",
        )
        topo.nodes.append(scanner)

        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content)

            # Scan info
            topo.scan_info = {
                "scanner": root.get("scanner", "nmap"),
                "args": root.get("args", ""),
                "start": root.get("startstr", ""),
            }

            subnet_nodes: Dict[str, TopoNode] = {}

            for host_elem in root.findall(".//host"):
                # Get IP address
                addr_elem = host_elem.find("address[@addrtype='ipv4']")
                if addr_elem is None:
                    addr_elem = host_elem.find("address[@addrtype='ipv6']")
                if addr_elem is None:
                    continue

                ip = addr_elem.get("addr", "")
                if not ip:
                    continue

                # Status
                status_elem = host_elem.find("status")
                status = status_elem.get("state", "up") if status_elem is not None else "up"

                # Hostname
                hostname = ""
                hostnames = host_elem.find("hostnames")
                if hostnames is not None:
                    hn = hostnames.find("hostname")
                    if hn is not None:
                        hostname = hn.get("name", "")

                # MAC address
                mac = ""
                mac_elem = host_elem.find("address[@addrtype='mac']")
                if mac_elem is not None:
                    mac = mac_elem.get("addr", "")

                # OS detection
                os_name = ""
                os_elem = host_elem.find(".//osmatch")
                if os_elem is not None:
                    os_name = os_elem.get("name", "")

                # Ports
                ports = []
                for port_elem in host_elem.findall(".//port"):
                    state_elem = port_elem.find("state")
                    service_elem = port_elem.find("service")

                    port_info: Dict[str, Any] = {
                        "port": int(port_elem.get("portid", 0)),
                        "protocol": port_elem.get("protocol", "tcp"),
                        "state": state_elem.get("state", "unknown") if state_elem is not None else "unknown",
                    }

                    if service_elem is not None:
                        port_info["service"] = service_elem.get("name", "")
                        port_info["product"] = service_elem.get("product", "")
                        port_info["version"] = service_elem.get("version", "")
                        port_info["extrainfo"] = service_elem.get("extrainfo", "")

                    if port_info["state"] == "open":
                        ports.append(port_info)

                # Create host node
                host_id = f"host_{ip.replace('.', '_').replace(':', '_')}"
                label = hostname or ip
                if ports:
                    label += f" ({len(ports)} ports)"

                host_node = TopoNode(
                    id=host_id,
                    label=label,
                    node_type="host",
                    ip=ip,
                    mac=mac,
                    hostname=hostname,
                    os=os_name,
                    ports=ports,
                    status=status,
                )

                # Subnet grouping
                subnet_id = self._get_subnet(ip)
                if subnet_id and subnet_id not in subnet_nodes:
                    subnet_node = TopoNode(
                        id=f"subnet_{subnet_id}",
                        label=subnet_id,
                        node_type="subnet",
                    )
                    subnet_nodes[subnet_id] = subnet_node
                    topo.nodes.append(subnet_node)
                    topo.edges.append(TopoEdge(
                        source="scanner",
                        target=f"subnet_{subnet_id}",
                        edge_type="scan",
                    ))

                topo.nodes.append(host_node)

                if subnet_id and subnet_id in subnet_nodes:
                    topo.edges.append(TopoEdge(
                        source=f"subnet_{subnet_id}",
                        target=host_id,
                        edge_type="connection",
                    ))
                else:
                    topo.edges.append(TopoEdge(
                        source="scanner",
                        target=host_id,
                        edge_type="scan",
                    ))

        except Exception:
            # If XML parsing fails, try text parsing
            return self.parse_nmap_text(xml_content)

        return topo

    def parse_masscan_output(self, output: str) -> NetworkTopology:
        """
        Parse masscan output into a NetworkTopology.
        Masscan format: Discovered open port <port>/<proto> on <ip>
        """
        topo = NetworkTopology()

        scanner = TopoNode(
            id="scanner",
            label=self.scanner_label,
            node_type="scanner",
        )
        topo.nodes.append(scanner)

        # Pattern: Discovered open port 80/tcp on 192.168.1.1
        pattern = re.compile(r"Discovered open port (\d+)/(\w+) on ([\d.]+)")
        hosts: Dict[str, TopoNode] = {}
        subnet_nodes: Dict[str, TopoNode] = {}

        for match in pattern.finditer(output):
            port = int(match.group(1))
            proto = match.group(2)
            ip = match.group(3)

            host_id = f"host_{ip.replace('.', '_')}"

            if host_id not in hosts:
                host_node = TopoNode(
                    id=host_id,
                    label=ip,
                    node_type="host",
                    ip=ip,
                    ports=[],
                )
                hosts[host_id] = host_node

                # Subnet
                subnet_id = self._get_subnet(ip)
                if subnet_id and subnet_id not in subnet_nodes:
                    sn = TopoNode(id=f"subnet_{subnet_id}", label=subnet_id, node_type="subnet")
                    subnet_nodes[subnet_id] = sn
                    topo.nodes.append(sn)
                    topo.edges.append(TopoEdge(source="scanner", target=f"subnet_{subnet_id}", edge_type="scan"))

                if subnet_id and subnet_id in subnet_nodes:
                    topo.edges.append(TopoEdge(source=f"subnet_{subnet_id}", target=host_id, edge_type="connection"))
                else:
                    topo.edges.append(TopoEdge(source="scanner", target=host_id, edge_type="scan"))

            hosts[host_id].ports.append({
                "port": port,
                "protocol": proto,
                "state": "open",
            })

        # Update labels and add to topology
        for host in hosts.values():
            host.label = f"{host.ip} ({len(host.ports)} ports)"
            topo.nodes.append(host)

        return topo

    def auto_parse(self, output: str) -> NetworkTopology:
        """
        Auto-detect scan format and parse accordingly.
        Tries XML first, then nmap text, then masscan.
        """
        stripped = output.strip()

        # Check for XML
        if stripped.startswith("<?xml") or stripped.startswith("<nmaprun"):
            return self.parse_nmap_xml(output)

        # Check for masscan output
        if "Discovered open port" in output:
            return self.parse_masscan_output(output)

        # Default to nmap text
        return self.parse_nmap_text(output)

    # ── ASCII Rendering ──────────────────────────────────────────────────

    @staticmethod
    def render_ascii(topo: NetworkTopology) -> str:
        """
        Render a network topology as ASCII art for terminal display.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("  NETWORK TOPOLOGY MAP")
        lines.append("=" * 60)

        hosts = [n for n in topo.nodes if n.node_type == "host"]
        subnets = [n for n in topo.nodes if n.node_type == "subnet"]

        stats = topo.to_dict()["stats"]
        lines.append(f"  Hosts: {stats['total_hosts']}  |  "
                      f"Services: {stats['total_services']}  |  "
                      f"Subnets: {stats['subnets']}")
        lines.append("-" * 60)

        if not hosts:
            lines.append("  No hosts discovered.")
            return "\n".join(lines)

        # Group hosts by subnet
        subnet_map: Dict[str, List[TopoNode]] = {"direct": []}
        for node in subnets:
            subnet_map[node.id] = []

        for edge in topo.edges:
            if edge.edge_type == "connection":
                target_node = next((n for n in hosts if n.id == edge.target), None)
                if target_node:
                    subnet_map.setdefault(edge.source, []).append(target_node)
            elif edge.edge_type == "scan":
                target_node = next((n for n in hosts if n.id == edge.target), None)
                if target_node:
                    subnet_map["direct"].append(target_node)

        lines.append("")
        lines.append(f"  [Scanner: {topo.nodes[0].label if topo.nodes else 'unknown'}]")
        lines.append("      |")

        for subnet_id, subnet_hosts in subnet_map.items():
            if not subnet_hosts:
                continue

            if subnet_id != "direct":
                subnet_label = subnet_id.replace("subnet_", "")
                lines.append(f"      +--- [{subnet_label}]")
                prefix = "      |    "
            else:
                prefix = "      "

            for i, host in enumerate(subnet_hosts):
                is_last = i == len(subnet_hosts) - 1
                connector = "└" if is_last else "├"

                # Host line
                host_label = host.ip
                if host.hostname:
                    host_label += f" ({host.hostname})"
                status_icon = "●" if host.status == "up" else "○"
                os_info = f" [{host.os}]" if host.os else ""

                lines.append(f"{prefix}{connector}── {status_icon} {host_label}{os_info}")

                # Port lines
                port_prefix = f"{prefix}{'   ' if is_last else '│  '}"
                open_ports = [p for p in host.ports if p.get("state") == "open"]

                for j, p in enumerate(open_ports[:15]):
                    port_line = f"{p['port']}/{p.get('protocol', 'tcp')}"
                    service = p.get("service", "")
                    product = p.get("product", "")
                    version = p.get("version", "")

                    if service:
                        port_line += f"  {service}"
                    if product:
                        port_line += f" ({product}"
                        if version:
                            port_line += f" {version}"
                        port_line += ")"

                    port_icon = "  ├─ " if j < len(open_ports) - 1 else "  └─ "
                    lines.append(f"{port_prefix}{port_icon}{port_line}")

                if len(open_ports) > 15:
                    lines.append(f"{port_prefix}  └─ ... and {len(open_ports) - 15} more ports")

                if not is_last:
                    lines.append(f"{prefix}│")

            lines.append(f"{'      |' if subnet_id != 'direct' else ''}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    @staticmethod
    def render_mermaid(topo: NetworkTopology) -> str:
        """
        Render a network topology as an interactive Mermaid diagram.
        """
        lines = [
            "```mermaid",
            "graph TD",
            "    %% Styles",
            "    classDef scanner fill:#1f6feb,stroke:#388bfd,stroke-width:2px,color:#fff;",
            "    classDef subnet fill:#21262d,stroke:#30363d,stroke-width:1px,color:#8b949e;",
            "    classDef host fill:#161b22,stroke:#58a6ff,stroke-width:1px,color:#c9d1d9;",
        ]

        if not topo.nodes:
            lines.append('    empty["(No hosts discovered)"]')
            lines.append("```")
            return "\n".join(lines)

        def safe_id(nid: str) -> str:
            return re.sub(r"[^a-zA-Z0-9_]", "_", nid)

        scanner_node = next((n for n in topo.nodes if n.node_type == "scanner"), None)
        scanner_id = safe_id(scanner_node.id if scanner_node else "scanner")
        scanner_label = scanner_node.label if scanner_node else "Scanner"
        lines.append(f'    {scanner_id}["⚡ {scanner_label}"]:::scanner')

        subnets = [n for n in topo.nodes if n.node_type == "subnet"]
        for s in subnets:
            safe_label = s.label.replace('"', "'")
            lines.append(f'    {safe_id(s.id)}["🌐 {safe_label}"]:::subnet')

        hosts = [n for n in topo.nodes if n.node_type == "host"]
        for h in hosts:
            open_ports = [p for p in h.ports if p.get("state") == "open"]
            host_text = h.ip
            if h.hostname:
                host_text += f"<br/>({h.hostname})"
            if open_ports:
                port_strs = [f"{p['port']}/{p.get('protocol', 'tcp')}" for p in open_ports[:4]]
                if len(open_ports) > 4:
                    port_strs.append(f"+{len(open_ports)-4} more")
                host_text += f"<br/>Ports: {', '.join(port_strs)}"
            if h.os:
                safe_os = h.os[:20].replace('"', "'")
                host_text += f"<br/>OS: {safe_os}"
            lines.append(f'    {safe_id(h.id)}["🖥️ {host_text}"]:::host')

        for edge in topo.edges:
            edge_lbl = f"|{edge.label}|" if edge.label else ""
            lines.append(f"    {safe_id(edge.source)} -->{edge_lbl} {safe_id(edge.target)}")

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def format_markdown(topo: NetworkTopology) -> str:
        """Format topology as a markdown summary."""
        lines = []
        stats = topo.to_dict()["stats"]

        lines.append("## 🗺️ Network Topology\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Hosts | {stats['total_hosts']} |")
        lines.append(f"| Open Services | {stats['total_services']} |")
        lines.append(f"| Subnets | {stats['subnets']} |")
        lines.append("")

        # Network Graph (Mermaid)
        lines.append("### Network Graph\n")
        lines.append(TopologyParser.render_mermaid(topo))
        lines.append("")

        hosts = [n for n in topo.nodes if n.node_type == "host"]

        if hosts:
            lines.append("### Discovered Hosts\n")
            lines.append("| IP | Hostname | OS | Open Ports | Status |")
            lines.append("|----|----------|-----|------------|--------|")

            for host in hosts:
                open_ports = [p for p in host.ports if p.get("state") == "open"]
                port_summary = ", ".join(
                    f"{p['port']}/{p.get('protocol', 'tcp')}"
                    for p in open_ports[:8]
                )
                if len(open_ports) > 8:
                    port_summary += f" +{len(open_ports) - 8} more"

                lines.append(
                    f"| {host.ip} | {host.hostname or '—'} | "
                    f"{host.os or '—'} | {port_summary or '—'} | {host.status} |"
                )
            lines.append("")

            # Detailed per-host service info
            for host in hosts:
                open_ports = [p for p in host.ports if p.get("state") == "open"]
                if not open_ports:
                    continue

                title = host.hostname or host.ip
                lines.append(f"#### 🖥️ {title} (`{host.ip}`)\n")
                if host.os:
                    lines.append(f"**OS:** {host.os}\n")

                lines.append("| Port | Service | Product | Version |")
                lines.append("|------|---------|---------|---------|")
                for p in open_ports:
                    lines.append(
                        f"| {p['port']}/{p.get('protocol', 'tcp')} | "
                        f"{p.get('service', '—')} | "
                        f"{p.get('product', '—')} | "
                        f"{p.get('version', '—')} |"
                    )
                lines.append("")

        return "\n".join(lines)

    # ── Internal ─────────────────────────────────────────────────────────

    def _parse_scan_header(self, output: str) -> Dict[str, Any]:
        """Parse nmap scan header info."""
        info: Dict[str, Any] = {}
        first_lines = output[:500].splitlines()[:5]
        for line in first_lines:
            if "Nmap scan report" in line or "Starting Nmap" in line:
                info["scanner"] = "nmap"
            if "scan report" in line.lower():
                match = re.search(r"for\s+(\S+)", line)
                if match:
                    info["target"] = match.group(1)
        return info

    def _split_host_blocks(self, output: str) -> List[str]:
        """Split nmap output into per-host blocks."""
        blocks = []
        current_block: List[str] = []

        for line in output.splitlines():
            if re.match(r"Nmap scan report for", line):
                if current_block:
                    blocks.append("\n".join(current_block))
                current_block = [line]
            elif current_block:
                current_block.append(line)

        if current_block:
            blocks.append("\n".join(current_block))

        return blocks

    def _parse_host_block(self, block: str) -> Optional[TopoNode]:
        """Parse a single nmap host block into a TopoNode."""
        lines = block.strip().splitlines()
        if not lines:
            return None

        # First line: Nmap scan report for <hostname> (<ip>) or just <ip>
        first_line = lines[0]
        ip = ""
        hostname = ""

        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", first_line)
        if ip_match:
            ip = ip_match.group(1)

        host_match = re.search(r"for\s+(\S+)", first_line)
        if host_match:
            name = host_match.group(1)
            if name != ip and not name.startswith("("):
                hostname = name

        if not ip:
            return None

        host_id = f"host_{ip.replace('.', '_')}"

        # Parse host status
        status = "up"
        for line in lines:
            if "Host is up" in line:
                status = "up"
            elif "Host seems down" in line:
                status = "down"

        # Parse ports
        ports = []
        port_pattern = re.compile(
            r"(\d+)/(\w+)\s+(open|closed|filtered)\s+(\S+)\s*(.*)"
        )
        for line in lines:
            match = port_pattern.match(line.strip())
            if match:
                port_info: Dict[str, Any] = {
                    "port": int(match.group(1)),
                    "protocol": match.group(2),
                    "state": match.group(3),
                    "service": match.group(4),
                }
                banner = match.group(5).strip()
                if banner:
                    # Try to extract product and version from banner
                    parts = banner.split()
                    if parts:
                        port_info["product"] = parts[0]
                    if len(parts) > 1:
                        port_info["version"] = parts[1]
                    port_info["banner"] = banner

                if port_info["state"] == "open":
                    ports.append(port_info)

        # Parse OS
        os_name = ""
        for line in lines:
            if line.strip().startswith("OS details:") or line.strip().startswith("Running:"):
                os_name = line.split(":", 1)[1].strip()
                break
            os_match = re.search(r"OS guess:\s*(.+)", line)
            if os_match:
                os_name = os_match.group(1)

        # Parse MAC
        mac = ""
        mac_match = re.search(r"MAC Address:\s*([\w:]+)", block)
        if mac_match:
            mac = mac_match.group(1)

        label = hostname or ip
        if ports:
            label += f" ({len(ports)} ports)"

        return TopoNode(
            id=host_id,
            label=label,
            node_type="host",
            ip=ip,
            mac=mac,
            hostname=hostname,
            os=os_name,
            ports=ports,
            status=status,
        )

    @staticmethod
    def _get_subnet(ip: str) -> str:
        """Extract /24 subnet from an IP address."""
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        return ""
