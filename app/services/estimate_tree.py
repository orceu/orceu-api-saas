from typing import List, Dict, Any

def ensure_stage_path(root_list: List[Dict[str, Any]], idx_parts: List[str]) -> Dict[str, Any]:
    current_list = root_list
    current_node = None
    for depth in range(len(idx_parts)):
        prefix = ".".join(idx_parts[:depth+1])
        found = None
        for item in current_list:
            if item.get("index") == prefix and item.get("estimate_item_type") == "stage":
                found = item
                break
        if not found:
            found = {
                "estimate_item_type": "stage",
                "index": prefix,
                "name": None,
                "price_total": None,
                "estimate_items": []
            }
            current_list.append(found)
        current_node = found
        current_list = found["estimate_items"]
    return current_node

def add_child_to_index(root_list: List[Dict[str, Any]], idx: str, child: Dict[str, Any]):
    parts = idx.split(".")
    if len(parts) == 1:
        root_list.append(child)
        return
    parent_parts = parts[:-1]
    parent_node = ensure_stage_path(root_list, parent_parts)
    parent_node["estimate_items"].append(child)