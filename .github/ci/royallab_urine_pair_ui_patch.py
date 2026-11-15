"""Surgical, urine-only two-controls-per-row renderer for original NOVA lab UI.

Run after royallab_typed_input_patch.py in Windows source assembly.
Crystals, Cast and Others retain BOTH original line IDs and independent inputs.
Other tests, saving, print reports and pharmacy code are untouched.
"""
from pathlib import Path

OLD = """rows.map(x=>'<tr><td><b>'+esc(x.name)+'</b></td>'+
      '<td>'+(editable?royalLabInput(x):'<b dir="auto">'+esc(x.value)+'</b>')+'</td>'+
      '<td dir="ltr">'+(esc(x.unit)||'—')+'</td>'+
      '<td dir="ltr" class="reference">'+(esc(x.reference_range)||'—')+'</td></tr>').join('')"""
NEW = "novaUrinePairedRows(rows,editable)"
HELPER = r"""
function novaUrinePairedRows(rows,editable){
  const single=x=>'<tr><td><b>'+esc(x.name)+'</b></td>'+
    '<td>'+(editable?royalLabInput(x):'<b dir="auto">'+esc(x.value)+'</b>')+'</td>'+
    '<td dir="ltr">'+(esc(x.unit)||'—')+'</td>'+
    '<td dir="ltr" class="reference">'+(esc(x.reference_range)||'—')+'</td></tr>';
  // These original SOURCE FORMAT IDs must all be present in the SAME
  // Microscopy section, otherwise use the pre-existing generic renderer.
  const codes=new Set((rows||[]).map(x=>String(x.code||'')));
  if(!['ROYAL_FMT_297','ROYAL_FMT_727','ROYAL_FMT_745',
       'ROYAL_FMT_746','ROYAL_FMT_555','ROYAL_FMT_409'].every(c=>codes.has(c)))
    return rows.map(single).join('');
  const matches=new Map(rows.map((x,i)=>[String(x.code||''),{x,i}]));
  const starts={
    'ROYAL_FMT_297':{second:'ROYAL_FMT_727',title:'Crystals',a:'Type',b:'Grade'},
    'ROYAL_FMT_745':{second:'ROYAL_FMT_746',title:'Cast',a:'Type',b:'Grade'},
    'ROYAL_FMT_555':{second:'ROYAL_FMT_409',title:'Others',a:'Grade',b:'Additional Notes'}
  };
  const handled=new Set();
  const control=x=>editable?royalLabInput(x):'<b dir="auto">'+esc(x.value)+'</b>';
  const meta=(a,b,k)=>[a[k],b[k]].map(v=>esc(v)||'—').join(' / ');
  let html='';
  for(let i=0;i<rows.length;i++){
    const x=rows[i];
    if(handled.has(x.id))continue;
    const setting=starts[String(x.code||'')];
    const found=setting?matches.get(setting.second):null;
    if(!found||found.i<=i||handled.has(found.x.id)){
      html+=single(x);
      continue;
    }
    const other=found.x;
    // Never merge underlying input identities: each widget keeps data-line.
    html+='<tr><td><b>'+esc(setting.title)+'</b></td>'+
      '<td><div class="nova-urine-pair" style="display:flex;flex-wrap:wrap;gap:12px">'+
        '<label style="display:flex;flex-direction:column;flex:1;min-width:135px">'+
          '<small>'+esc(setting.a)+'</small>'+control(x)+'</label>'+
        '<label style="display:flex;flex-direction:column;flex:1;min-width:135px">'+
          '<small>'+esc(setting.b)+'</small>'+control(other)+'</label>'+
      '</div></td>'+
      '<td dir="ltr">'+meta(x,other,'unit')+'</td>'+
      '<td dir="ltr" class="reference">'+meta(x,other,'reference_range')+'</td></tr>';
    handled.add(x.id);handled.add(other.id);
  }
  return html;
}
"""

def patch(source):
    if "function novaUrinePairedRows(" in source:
        raise ValueError("Urine paired display already applied")
    if source.count("function novaLabGroupedRows(lines,editable)") != 1:
        raise ValueError("Expected original NOVA grouped laboratory table renderer")
    if source.count("function royalLabInput(x)") != 1:
        raise ValueError("Typed Royal Lab inputs must be patched first")
    if source.count(OLD) != 1:
        raise ValueError("Unexpected NOVA result renderer; do not guess UI anchors")
    return HELPER + source.replace(OLD, NEW, 1)


def apply(root):
    path = Path(root) / "hospital/static/app.js"
    path.write_text(patch(path.read_text(encoding="utf-8")), encoding="utf-8")
    return path


if __name__ == "__main__":
    apply(Path(__file__).resolve().parents[2])
