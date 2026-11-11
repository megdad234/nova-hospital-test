"""Bundle pinned original Royal Lab files into NOVA's Windows build.

Requires access to the RoyalLab-Recovery source repository. Fail closed on
unavailable files or changed Git blob IDs. No patient data is imported.
"""
import argparse,hashlib,json,os,pathlib,urllib.request
COMMIT="49724fa445d7043276abe4e443c403d3f592bfa5"
BASE="https://raw.githubusercontent.com/megdad234/Royallab-Recovery/"+COMMIT+"/output/nova_library/"
SOURCES={
 "nova_lab_library.json":"fb4c5868647cad9566269f388ced12e33311e419",
 "unlinked_options.json":"83235fa9548c08fddb13bb6661636af669d20eb7"
}
def git_blob_id(data):
 return hashlib.sha1(b"blob "+str(len(data)).encode()+bytes([0])+data).hexdigest()
def bundle(root,token=None):
 root=pathlib.Path(root)
 destination=root/"hospital"/"royallab_source"
 destination.mkdir(parents=True,exist_ok=True)
 report={"upstream_commit":COMMIT,"files":{}}
 for name,expected in SOURCES.items():
  req=urllib.request.Request(BASE+name,headers={"User-Agent":"NOVA-RoyalLab-pinned-source-bundler"})
  if token:req.add_header("Authorization","Bearer "+token)
  with urllib.request.urlopen(req,timeout=120) as response:data=response.read()
  if git_blob_id(data)!=expected:
   raise RuntimeError("Royal Lab source changed or corrupted: "+name)
  json.loads(data.decode("utf-8-sig"))
  target=destination/name
  target.write_bytes(data)
  report["files"][name]={"path":"hospital/royallab_source/"+name,
                        "sha256":hashlib.sha256(data).hexdigest(),
                        "git_blob":expected,"bytes":len(data)}
 (destination/"source_provenance.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",default=".")
 args=p.parse_args()
 print(json.dumps(bundle(args.root,os.environ.get("ROYALLAB_SOURCE_TOKEN")),indent=2))
