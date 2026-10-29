# Historical adapter

These are the scripts actually used for the recorded forcing, retained here for comparison with the portable version. Absolute local paths are replaced by angle-bracket placeholders; this is a reading copy, not a standalone executable. The hashes of the original unedited files are in `provenance.json`. No scientific statements in historical stage messages have been updated retrospectively.

`O` denotes the original stage directory, `SOURCE` its unchanged v0.4.1 source copy, and `ARCH` its output archive. `common`, `builder` and `static_builder` are the three native ERA5 helper modules imported by `prepare_archive.py`. `parse` decodes the saved GDEX DAP responses; `sha` and `save` record checksums and JSON evidence.

## build_arco_archive.py

```python
from prepare_archive import *
import calendar,subprocess
start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
prepare_static();builder.CHUNK=1;static=builder.load_static(str(ARCH))
series={};dates=None
for p in sorted((O/'arco_raw').glob('*/point_2003_2022.npz')):
 with np.load(p) as d:
  if dates is None:dates=d['time'].copy()
  else:assert np.array_equal(dates,d['time'])
  for raw in common.VARIABLES:
   if raw in d:series[raw]=d[raw].astype('f4')
assert len(series)==8 and len(dates)==175320
save('checks/processing_contract.json',{'source_release':'v0.4.1','commit':'f49d50c89f01e5747eee2950a9cbe1d8e08371a5','scientific_variable_or_parameter_changes':[],'transport':'Official ECMWF ERA5-Land ARCO spatial subset, exact overlap comparison with official GDEX d633008. All raw chunks retained.','flux_semantics':'ECMWF ARCO already deaccumulates tp/ssrd/strd. Apply author clipping and factor once, without a second difference.','native_operations':['write_static for orography and coordinates','ARCHIVE_VARIABLES factors, clip_negative, bounds and precision','check_band and create_output (GranularBitRound)','finish_output and native make_forcing_file.py --data-path'],'engineering_adjustments':['One-cell regional archive, CHUNK=1 instead of 16; spatial storage only','Assign already-deaccumulated ARCO values to native archive output; write_bands is not called because it would difference them again'],'scope':'BCI only; 2003-2022 complete original recycle period; no Example05 run/optimization.','comparison_boundary':'Sampled exact agreement does not prove unqueried GDEX hours are bitwise equal.'})
results=[]
for y in range(2003,2023):
 for m in range(1,13):
  first,last=common.month_interval(y,m);expect=[first+datetime.timedelta(hours=i) for i in range(common.stamps_between(first,last))];ix=np.searchsorted(dates,np.array(expect,dtype='datetime64[s]'));assert np.array_equal(dates[ix],np.array(expect,dtype='datetime64[s]'))
  for name,spec in common.ARCHIVE_VARIABLES.items():
   out=Path(common.archive_file(str(ARCH),name,y,m));assert not out.exists(),out
   a=series[spec['raw']][ix,None,None].copy();negative=int((a<0).sum()) if spec['kind']=='accum' else 0
   if spec['kind']=='accum':
    if spec['clip_negative']:np.maximum(a,0,out=a)
    a*=np.float32(spec['factor'])
   lo,hi=builder.check_band(a,static[2],spec['bounds'],0,1,static[0],static[1])
   dst,v=builder.create_output(str(out)+'.part',name,spec,static,expect);v[:]=a
   builder.finish_output(dst,name,y,m,'ECMWF Copernicus ERA5-Land ARCO point subset, doi:10.24381/cds.e2161bac; hourly deaccumulation by ECMWF; native ED-MORE precision and units',str(O/'arco_raw'),[])
   n,h=builder.publish(str(out)+'.part',str(out));results.append({'path':str(out.relative_to(O)),'sha256':h,'bytes':n,'name':name,'year':y,'month':m,'hours':len(expect),'min_before_quantization':lo,'max_before_quantization':hi,'negative_raw_hourly':negative,'native_bounds_pass':True})
save('archive_manifest.json',{'files':results,'variable_months':len(results),'source':'arco','period_hours':len(dates),'wall_seconds':time.monotonic()-start,'start_utc':utc,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
ready=O/'prepared';ready.mkdir(exist_ok=True)
cmd=[sys.executable,str(SOURCE/'scripts/prepare_input/era5/make_forcing_file.py'),'--data-path',str(ARCH),'--start','2003-01-01','--end','2022-12-31','--lat','9.1568','--lon','-79.8486','--out',str(ready/'bci_era5land_2003-2022.nc')]
assert not (ready/'bci_era5land_2003-2022.nc').exists();t=time.monotonic()
with (O/'native_make_forcing.log').open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
save('native_make_forcing_command.json',{'command':cmd,'exit_code':r.returncode,'wall_seconds':time.monotonic()-t});assert r.returncode==0
for name in ['bci_2005_census.csv','growth.csv.gz']:
 p=Path('<LOCAL_CENSUS_STAGE>')/name;shutil.copy2(p,ready/name)
save('prepared_files.json',{'files':[{'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(ready.iterdir())],'model_run':False})
print('Full-period native-format forcing and census inputs prepared; final validation pending.',flush=True)
```

## prepare_archive.py: static-cell preparation

```python
def prepare_static():
 if (ARCH/'ED_ERA5land_static.nc').exists():return
 vals={}
 for name in ['z','lsm']:
  p=O/f'raw_subsets/static/{name}.dods';d,h=parse(p.read_bytes());vals[name]=float(d[name][0,0,0])
 # The nearest coordinate cell has finite Tair at all 120 hours in the 5x5 probe.
 lines=(O/'public_sources/t2m_grid_probe_encoded.txt').read_text().splitlines()
 array=[]
 for line in lines:
  if re.match(r'^\[\d+\]\[\d+\],',line):array.extend(float(x) for x in line.split(',')[1:])
 a=np.array(array).reshape(120,5,5);valid=np.isfinite(a).all(0);lat=np.array([9.4,9.3,9.2,9.1,9.0]);lon=np.array([-80,-79.9,-79.8,-79.7,-79.6])
 sys.path.insert(0,str(SOURCE/'scripts/prepare_input/era5'));import make_forcing_file as maker
 distances=maker.great_circle_km(9.1568,-79.8486,lat[:,None],lon[None,:]);distances[~valid]=np.inf
 i,j=np.unravel_index(np.argmin(distances),distances.shape);assert (i,j)==(2,2);assert distances[i,j]<15
 elevation=np.array([[vals['z']/9.80665]],dtype='f4')
 static_builder.write_static(str(ARCH/'ED_ERA5land_static.nc'),np.array([9.2]),np.array([-79.8]),np.array([[1]],dtype='i1'),elevation,np.array([[vals['lsm']]],dtype='f4'),'spatial subset of GDEX 200501 t2m, all 120 hours finite at nearest coordinate cell')
 save('checks/selected_cell.json',{'site':[9.1568,-79.8486],'cell':[9.2,-79.8],'distance_km':float(distances[i,j]),'grid_indices':[808,2802],'geopotential_m2_s2':vals['z'],'elevation_float32_m':float(elevation[0,0]),'land_fraction':vals['lsm'],'all_120_probe_hours_finite_at_nearest_cell':True,'selection':'Nearest coordinate cell is valid; hence also nearest valid cell on global regular grid. Full-period validity checked for every downloaded hour.'})
 save('checks/processing_contract.json',{'source_release':'v0.4.1','commit':'f49d50c89f01e5747eee2950a9cbe1d8e08371a5','scientific_changes':[],'engineering_adapter':['Anonymous official GDEX DAP2 spatial subset transport instead of global full-file download','Native archive builder CHUNK=1 instead of 16, spatial storage layout only','Input read_band supplied from exact float32 DAP values with all original hourly stamps'],'native_operations':['write_static: z/9.80665 then float32','write_bands: native deaccumulate, clipping, conversion and bounds','create_output: native significant_digits and GranularBitRound','make_forcing_file.py --data-path for final site file'],'scope':'BCI only, 2003-01-01 01:00 to 2023-01-01 00:00 UTC. No Example05 model or fitting.'})
```
