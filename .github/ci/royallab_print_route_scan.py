"""Read-only scan of NOVA source ZIP for laboratory report HTML routes."""
import pathlib,zipfile
root=pathlib.Path(__file__).resolve().parents[2]
terms=("تقرير جزئي","توجد فحوصات أخرى","lab/report","lab_report","lab.report","lab_report_print","printLabReport","report_lab","labReport","/api/lab")
with zipfile.ZipFile(root/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
 for name in z.namelist():
  if name.endswith("/") or not name.lower().endswith((".py",".html",".js",".css")):continue
  if z.getinfo(name).file_size>2_000_000:continue
  try:lines=z.read(name).decode("utf-8-sig").splitlines()
  except UnicodeDecodeError:continue
  hits=[(i+1,line.strip()[:200]) for i,line in enumerate(lines) if any(t in line for t in terms)]
  if hits:
   print("FILE",name,"HITS",len(hits))
   for lineno,line in hits[:22]:print(lineno,line)
