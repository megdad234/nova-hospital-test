"""Validate Royal Lab -> NOVA line mappings against an existing order item.
Read-only: does not create lines, update results or bypass original NOVA save.
"""
def verify_line_mapping(conn,item_id,source_to_line):
    if type(item_id) is not int or item_id<=0:raise ValueError("Invalid order item")
    if not isinstance(source_to_line,dict) or not source_to_line:
        raise ValueError("Reviewed source-to-line mapping required")
    if len(set(source_to_line.values()))!=len(source_to_line):
        raise ValueError("Duplicate NOVA line mapping")
    rows=conn.execute("SELECT id,code,name,unit FROM hospital_lab_lines WHERE item_id=?",(item_id,)).fetchall()
    available={int(row[0]):{"code":row[1],"name":row[2],"unit":row[3]} for row in rows}
    missing=[key for key,line_id in source_to_line.items() if type(line_id) is not int or line_id not in available]
    if missing:raise ValueError("Mapped NOVA lines do not belong to this order item: "+", ".join(map(str,missing)))
    return {"item_id":item_id,"verified":True,"mapped_count":len(source_to_line),
            "mapped_lines":{key:available[line_id] for key,line_id in source_to_line.items()},
            "clinical_approval":False}
