"""Document Knowledge Graph & Entity Relationship Linker Engine.

Builds a global graph database model linking documents by shared identifiers:
- Shared Aadhaar / PAN / Enrollment Numbers
- Shared Application IDs / Transaction Hashes
- Shared Person Names / Phone Numbers / Emails
"""

from typing import Dict, Any, List
from app import database


def generate_document_knowledge_graph(user_id: int = 1) -> Dict[str, Any]:
    """
    Constructs a global Knowledge Graph (Nodes = Documents & Entities, Edges = Relationships)
    representing cross-document links across the user's document repository.
    """
    images = database.list_images()
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    
    entity_map: Dict[str, List[Dict[str, Any]]] = {}

    for img in images:
        doc_id = img["id"]
        doc_name = img["image_name"]
        category = img.get("category", "General")
        
        # Add Document Node
        nodes.append({
            "id": f"doc_{doc_id}",
            "label": doc_name,
            "type": "DOCUMENT",
            "category": category,
            "image_url": f"/uploads/{doc_name}",
        })

        # Extract entities
        entities = img.get("entities", {})
        if isinstance(entities, dict):
            for ent_type, vals in entities.items():
                if isinstance(vals, list):
                    for v in vals:
                        val_str = str(v).strip()
                        if val_str and len(val_str) > 2:
                            key = f"{ent_type}:{val_str.lower()}"
                            if key not in entity_map:
                                entity_map[key] = []
                            entity_map[key].append({"doc_id": doc_id, "doc_name": doc_name, "type": ent_type, "val": val_str})

    # Add Entity Nodes & Connecting Edges
    edge_set = set()
    for key, matches in entity_map.items():
        if len(matches) >= 2:  # Shared entity linking 2 or more documents
            ent_type, ent_val = key.split(":", 1)
            ent_node_id = f"ent_{key}"
            
            nodes.append({
                "id": ent_node_id,
                "label": ent_val.upper(),
                "type": "ENTITY",
                "entity_type": ent_type,
            })

            for m in matches:
                doc_node_id = f"doc_{m['doc_id']}"
                edge_id = f"{doc_node_id}-->{ent_node_id}"
                if edge_id not in edge_set:
                    edge_set.add(edge_id)
                    edges.append({
                        "source": doc_node_id,
                        "target": ent_node_id,
                        "relationship": f"HAS_{ent_type.upper()}",
                        "label": ent_type.replace("_", " ").title(),
                    })

    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "linked_entity_groups": len([k for k, v in entity_map.items() if len(v) >= 2]),
        "nodes": nodes,
        "edges": edges,
    }
