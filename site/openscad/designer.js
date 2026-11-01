import { ensureViewerModules } from "../viewer.js";

const noseKeys = ["visible_length_mm", "insertion_length_mm", "insertion_diameter_mm", "base_diameter_mm", "tip_diameter_mm", "round_radius_mm"];
const capKeys = ["length_mm", "diameter_mm", "tip_diameter_mm", "insertion_length_mm", "insertion_diameter_mm", "round_radius_mm"];
const names = {visible_length_mm:"Visible length",insertion_length_mm:"Insertion length",insertion_diameter_mm:"Insertion diameter",base_diameter_mm:"Base diameter",tip_diameter_mm:"Tip diameter",round_radius_mm:"Rounded edge radius",length_mm:"Cap length",diameter_mm:"Cap diameter"};
const defaults = {nose_cone:{visible_length_mm:11,insertion_length_mm:5.9,insertion_diameter_mm:7.57,base_diameter_mm:10.2,tip_diameter_mm:5,passage_diameter_mm:4.9,stop_diameter_mm:3,stop_depth_mm:7,round_radius_mm:0.4},end_cap:{length_mm:2,diameter_mm:10.2,tip_diameter_mm:7.57,insertion_length_mm:5.9,insertion_diameter_mm:7.57,round_radius_mm:0.4}};
const $ = id => document.getElementById(id);
const data = await fetch(`designer-data.json?v=${Date.now()}`).then(r => {if (!r.ok) throw Error("Catalog failed to load");return r.json()});
const REFILL_COLORS=["#ffbd66","#72d9c7","#d6a6f3","#f092a4","#a9c7ff"];
const BORE_COLORS=["#8da9cd","#78b7b1","#a9a0d5","#8da9cd"];
let initialRefill = new URLSearchParams(location.search).get("refill");
let currentPen, currentRefill, three, baseNose, currentBore=[], manualBore=false, boreHash="", refillDraftError=false, boreDraftError=false, selectedSection=null, projectionCustomized=false;
function option(select,value,label){const el=document.createElement("option");el.value=value;el.textContent=label;select.append(el)}
function numericFields(container,keys,values){container.replaceChildren();for(const key of keys){const label=document.createElement("label");label.textContent=`${names[key] || key} (mm)`;const input=document.createElement("input");input.type="number";input.step="0.1";input.min="0";input.dataset.key=key;input.value=values[key]??"";const slider=document.createElement("input");slider.type="range";slider.min="0";slider.max=key.includes("length")?"150":key.includes("radius")?"3":"30";slider.step="0.1";slider.value=input.value;input.addEventListener("input",()=>{slider.value=input.value;update()});slider.addEventListener("input",()=>{input.value=slider.value;update()});label.append(input,slider);container.append(label)}}
function attachSlider(id,max,step){const input=$(id),slider=document.createElement("input");slider.type="range";slider.min="0";slider.max=String(max);slider.step=String(step);slider.value=input.value;input.after(slider);input.addEventListener("input",()=>{if(id==="tip-projection")projectionCustomized=true;slider.value=input.value;update()});slider.addEventListener("input",()=>{if(id==="tip-projection")projectionCustomized=true;input.value=slider.value;update()})}
function setProjectionDefault(refill,explicit){const first=refill?.segments?.[0]?.end_distance_mm;const value=explicit??(Number.isFinite(first)?first:0);$("tip-projection").value=value;$("tip-projection").nextElementSibling.value=value}
function readFields(container){return Object.fromEntries([...container.querySelectorAll('input[type="number"]')].map(i=>[i.dataset.key,Number(i.value)]))}
function withStarts(segments){let start=0;return (segments||[]).map(seg=>{const item={...seg,start_distance_mm:start};start=seg.end_distance_mm;return item})}
function profile(refill){return refill?.geometry_ready?withStarts(refill.segments):[]}
function diameterAt(seg,distance){if(seg.kind!=="taper")return seg.diameter_mm;const t=(distance-seg.start_distance_mm)/(seg.end_distance_mm-seg.start_distance_mm);return seg.diameter_start_mm+(seg.diameter_end_mm-seg.diameter_start_mm)*t}
function maxDiameter(seg){return seg.kind==="taper"?Math.max(seg.diameter_start_mm,seg.diameter_end_mm):seg.diameter_mm}
function deriveBore(refill,projection,tipClearance,passageClearance,noseTotal){
 const parts=profile(refill);if(!parts.length)return null;
 const maxBetween=(from,to)=>{let largest=0;for(const part of parts){const start=Math.max(from,part.start_distance_mm),end=Math.min(to,part.end_distance_mm);if(end<=start)continue;largest=Math.max(largest,diameterAt(part,start),diameterAt(part,end))}return largest};
 const candidates=[];
 for(let i=1;i<parts.length;i++){
  const distance=parts[i].start_distance_mm-projection;
  if(distance<=0.01||distance>=noseTotal-0.01)continue;
  const before=diameterAt(parts[i-1],parts[i-1].end_distance_mm),after=diameterAt(parts[i],parts[i].start_distance_mm);
  if(after-before>0.05)candidates.push({distance,jump:after-before});
 }
 candidates.sort((a,b)=>b.jump-a.jump||b.distance-a.distance);
 const shoulder=candidates[0]?.distance;
 if(shoulder===undefined){const diameter=maxBetween(projection,projection+noseTotal)+passageClearance;return [{kind:"cylinder",diameter_mm:Number(diameter.toFixed(3)),end_distance_mm:Number(noseTotal.toFixed(3))}]}
 const front=maxBetween(projection,projection+shoulder)+tipClearance;
 const rear=Math.max(maxBetween(projection+shoulder,projection+noseTotal)+passageClearance,front+0.1);
 return [{kind:"cylinder",diameter_mm:Number(front.toFixed(3)),end_distance_mm:Number(shoulder.toFixed(3))},{kind:"cylinder",diameter_mm:Number(rear.toFixed(3)),end_distance_mm:Number(noseTotal.toFixed(3))}];
}
function legacyBore(nose){return [{kind:"cylinder",diameter_mm:nose.stop_diameter_mm,end_distance_mm:nose.stop_depth_mm},{kind:"cylinder",diameter_mm:nose.passage_diameter_mm,end_distance_mm:nose.visible_length_mm+nose.insertion_length_mm}]}
function segmentValues(seg){return seg.kind==="taper"?[seg.diameter_start_mm,seg.diameter_end_mm,seg.end_distance_mm]:[seg.diameter_mm,"",seg.end_distance_mm]}
function readTable(id){const rows=[...$(id).querySelectorAll(".designer__table-row")];const segments=[];let partial=false;for(const row of rows){const [start,end,distance]=[...row.querySelectorAll("input")].map(i=>i.value.trim());if(!start&&!end&&!distance)continue;if(!distance){partial=true;continue}if(!start&&!end){if(id==="segments"&&currentRefill?.measurement_status==="incomplete")segments.push({kind:"cylinder",end_distance_mm:Number(distance)});else partial=true;continue}const seg=start&&end?{kind:"taper",diameter_start_mm:Number(start),diameter_end_mm:Number(end),end_distance_mm:Number(distance)}:{kind:"cylinder",diameter_mm:Number(start||end),end_distance_mm:Number(distance)};segments.push(seg)}return {segments,partial}}
function addTableRow(container,values,editable,onChange,kind=null,index=null){const row=document.createElement("div");row.className="designer__table-row";if(kind!==null){row.dataset.sectionKind=kind;row.dataset.sectionIndex=String(index)}for(const [column,value] of values.entries()){const input=document.createElement("input");input.type="number";input.min="0";input.step="0.1";input.value=value??"";input.setAttribute("aria-label",["Starting diameter (mm)","Ending diameter (mm)","End distance from tip (mm)"][column]);input.disabled=!editable;input.addEventListener("input",()=>{if(row===container.lastElementChild&&[...row.querySelectorAll("input")].some(i=>i.value.trim()))addTableRow(container,["","",""],editable,onChange);onChange()});row.append(input)}container.append(row)}
function renderTable(id,segments,editable,onChange){const container=$(id);container.replaceChildren();const header=document.createElement("div");header.className="designer__table-head";for(const label of ["Start Ø (mm)","End Ø (mm)","End from tip (mm)"]){const cell=document.createElement("span");cell.textContent=label;header.append(cell)}container.append(header);for(const [index,seg] of segments.entries())addTableRow(container,segmentValues(seg),editable,onChange,id==="segments"?"refill":"bore",index);if(editable)addTableRow(container,["","",""],editable,onChange);applySelection()}
function renderRefillDimensions(segments){const container=$("segments");container.replaceChildren();const header=document.createElement("div");header.className="designer__table-head";for(const label of ["Start Ø","End Ø","End from tip"]){const cell=document.createElement("span");cell.textContent=label;header.append(cell)}container.append(header);for(const [index,seg] of segments.entries()){const row=document.createElement("div");row.className="designer__table-row designer__table-row--read-only";row.dataset.sectionKind="refill";row.dataset.sectionIndex=String(index);for(const value of segmentValues(seg)){const cell=document.createElement("span");cell.textContent=value===""?"—":`${value} mm`;row.append(cell)}container.append(row)}applySelection()}
function refreshRowIndices(id){let index=0;for(const row of $(id).querySelectorAll(".designer__table-row")){if([...row.querySelectorAll("input")].some(input=>input.value.trim())){row.dataset.sectionKind=id==="segments"?"refill":"bore";row.dataset.sectionIndex=String(index++)}else{delete row.dataset.sectionKind;delete row.dataset.sectionIndex}}}
function applySelection(){document.querySelectorAll(".is-selected").forEach(el=>el.classList.remove("is-selected"));if(!selectedSection)return;const {kind,index}=selectedSection;const selector=index===undefined?`[data-section-kind="${kind}"]`:`[data-section-kind="${kind}"][data-section-index="${index}"]`;for(const el of document.querySelectorAll(selector))el.classList.add("is-selected");const card={nose:"panel-nose",bore:"panel-nose",body:"panel-body",cap:"panel-cap"}[kind];if(card)$(card).classList.add("is-selected")}
function selectSection(kind,index,scroll=false){if(kind==="bore")document.querySelector(".designer__bore-details").open=true;selectedSection={kind,index};applySelection();if(scroll&&(kind==="refill"||kind==="bore"||innerWidth<1050)){const card={nose:"panel-nose",body:"panel-body",cap:"panel-cap"}[kind];const target=card?$(card):$(kind==="refill"?"segments":"bore-segments").querySelector(`.designer__table-row[data-section-index="${index}"]`);target?.scrollIntoView({behavior:"smooth",block:"center"})}}
function refillIssues(r){if(!r)return ["Choose or create a refill"];const out=[];if(refillDraftError)out.push("Finish the partially entered refill row");if(!/^[a-z0-9_-]+$/.test(r.id||""))out.push("Refill ID must be a lowercase slug");for(const key of ["brand","model","format"])if(!r[key]?.trim())out.push(`${key} is required`);if(!r.segments?.length&&r.measurement_status!=="incomplete")out.push("Enter at least one segment");let last=0;for(const [index,seg] of (r.segments||[]).entries()){const fields=seg.kind==="taper"?["diameter_start_mm","diameter_end_mm","end_distance_mm"]:["diameter_mm","end_distance_mm"];for(const key of fields)if(!(seg[key]>0)&&r.measurement_status!=="incomplete")out.push(`Segment ${index+1}: ${key} must be positive`);if(!(seg.end_distance_mm>last))out.push(`Segment ${index+1}: end distance must increase`);last=seg.end_distance_mm}return out}
function syncRefillRows(){if(!currentRefill)currentRefill={id:"",brand:"",model:"",format:"",measurement_status:"incomplete",segments:[]};const parsed=readTable("segments");currentRefill.segments=parsed.segments;refillDraftError=parsed.partial;refreshRowIndices("segments");if(!projectionCustomized)setProjectionDefault(currentRefill);currentRefill.geometry_ready=currentRefill.measurement_status!=="incomplete"&&!refillIssues(currentRefill).length;update()}
function renderBore(){renderTable("bore-segments",currentBore,manualBore,syncBoreRows);$("customize-bore").hidden=manualBore;$("reset-bore").hidden=!manualBore}
function syncBoreRows(){const parsed=readTable("bore-segments");currentBore=parsed.segments;boreDraftError=parsed.partial;refreshRowIndices("bore-segments");update()}
function getState(){const nose=readFields($("nose-fields")),cap=readFields($("cap-fields")),projection=Number($("tip-projection").value),tipClearance=Number($("tip-clearance").value),passageClearance=Number($("passage-clearance").value);if(!manualBore){const derived=deriveBore(currentRefill,projection,tipClearance,passageClearance,nose.visible_length_mm+nose.insertion_length_mm);const next=derived||legacyBore({...baseNose,...nose});const hash=JSON.stringify(next);if(hash!==boreHash){currentBore=next;boreHash=hash;renderBore()}}nose.bore_segments=structuredClone(currentBore);return {nose,cap,bodyDiameter:Number($("body-diameter").value),bodyLength:Number($("body-length").value),projection,tipClearance,passageClearance,refill:currentRefill,designTitle:$("design-title").value.trim(),designId:currentPen.config.id||currentPen.id}}
function validate(s){const issues=[];for(const [label,obj] of [["Nose",s.nose],["Cap",s.cap]])for(const [key,value] of Object.entries(obj))if(key!=="bore_segments"&&(!Number.isFinite(value)||value<0||(value===0&&!key.includes("round_radius"))))issues.push(`${label}: ${names[key]||key} must be positive`);
 if(!s.designTitle)issues.push("Design name is required");
 if(!Number.isFinite(s.projection)||s.projection<0||!Number.isFinite(s.tipClearance)||s.tipClearance<0||!Number.isFinite(s.passageClearance)||s.passageClearance<0)issues.push("Projection and clearances must be nonnegative");
 if(s.bodyDiameter<=0||s.bodyLength<=0)issues.push("Wood body dimensions must be positive");
 if(s.nose.insertion_diameter_mm>=s.nose.base_diameter_mm)issues.push("Nose insertion must be narrower than its base");
 if(s.cap.insertion_diameter_mm>=s.cap.diameter_mm)issues.push("Cap insertion must be narrower than its outside");
 if(s.nose.round_radius_mm>=Math.min(s.nose.tip_diameter_mm/4,s.nose.insertion_length_mm/2,s.nose.visible_length_mm/2)||s.cap.round_radius_mm>=Math.min(s.cap.tip_diameter_mm/4,s.cap.insertion_length_mm/2,s.cap.length_mm/2))issues.push("Rounded edge radius exceeds the profile limit");
 const bore=withStarts(s.nose.bore_segments),noseTotal=s.nose.visible_length_mm+s.nose.insertion_length_mm;
 if(boreDraftError)issues.push("Finish the partially entered bore row");
 if(!bore.length)issues.push("Nose bore needs at least one segment");
 const outerAt=x=>x<s.nose.visible_length_mm?s.nose.tip_diameter_mm+(s.nose.base_diameter_mm-s.nose.tip_diameter_mm)*x/s.nose.visible_length_mm:s.nose.insertion_diameter_mm;
 for(const [index,seg] of bore.entries()){if(!(seg.end_distance_mm>seg.start_distance_mm))issues.push(`Bore row ${index+1}: end distance must increase`);for(const value of seg.kind==="taper"?[seg.diameter_start_mm,seg.diameter_end_mm]:[seg.diameter_mm])if(!(value>0))issues.push(`Bore row ${index+1}: diameter must be positive`);for(const x of [seg.start_distance_mm,seg.end_distance_mm,Math.min(Math.max(s.nose.visible_length_mm,seg.start_distance_mm),seg.end_distance_mm)])if(diameterAt(seg,x)>=outerAt(x)-1.2)issues.push(`Bore row ${index+1}: less than 0.6 mm nose wall`)}
 if(bore.length&&Math.abs(bore.at(-1).end_distance_mm-noseTotal)>0.001)issues.push("Last bore end must equal nose visible plus insertion length");
 const tubeDiameter=Math.max(s.nose.insertion_diameter_mm,s.cap.insertion_diameter_mm)+0.4;
 if(tubeDiameter>=s.bodyDiameter)issues.push("Body is too narrow for the insertion tube");
 if(s.refill){if(!s.refill.geometry_ready)issues.push("Refill measurements are incomplete");const parts=profile(s.refill);for(const fill of parts)for(const hole of bore){const start=Math.max(fill.start_distance_mm-s.projection,hole.start_distance_mm),end=Math.min(fill.end_distance_mm-s.projection,hole.end_distance_mm);if(end>start&&Math.max(diameterAt(fill,start+s.projection)-diameterAt(hole,start),diameterAt(fill,end+s.projection)-diameterAt(hole,end))>=0)issues.push("Refill intersects the nose bore")}
 if(parts.length&&parts.at(-1).end_distance_mm-s.projection>s.nose.visible_length_mm+s.bodyLength-s.cap.insertion_length_mm){const minimum=parts.at(-1).end_distance_mm-s.projection-s.nose.visible_length_mm+s.cap.insertion_length_mm;issues.push(`Refill reaches the end cap; body length must be at least ${minimum.toFixed(1)} mm`)}
 for(const fill of parts){const start=Math.max(fill.start_distance_mm-s.projection,noseTotal),end=Math.min(fill.end_distance_mm-s.projection,s.nose.visible_length_mm+s.bodyLength-s.cap.insertion_length_mm);if(end>start&&Math.max(diameterAt(fill,start+s.projection),diameterAt(fill,end+s.projection))>=tubeDiameter)issues.push("Refill is wider than the body tube")}}
 return [...new Set(issues)]}
function renderValidation(s,issues){
 document.querySelectorAll(".designer__field-error").forEach(node=>node.remove());
 document.querySelectorAll('[aria-invalid="true"]').forEach(node=>node.removeAttribute("aria-invalid"));
 const summary=$("validation");
 summary.textContent=issues.length?`${issues.length} design ${issues.length===1?"issue":"issues"} to fix. See the highlighted controls below.`:"Geometry is ready to export.";
 const shown=new Set();
 function mark(target,message){
  const element=typeof target==="string"?document.querySelector(target):target;
  if(!element)return;
  const holder=element.closest("label")||element.closest(".designer__table-row")||element;
  const key=`${message}|${holder.id||holder.outerHTML.slice(0,80)}`;
  if(shown.has(key))return;shown.add(key);
  const note=document.createElement("div");note.className="designer__field-error";note.textContent=message;
  holder.append(note);
  if(element.matches("input,select"))element.setAttribute("aria-invalid","true");
  else holder.querySelectorAll("input").forEach(input=>input.setAttribute("aria-invalid","true"));
 }
 const noseField=key=>`#nose-fields [data-key="${key}"]`,capField=key=>`#cap-fields [data-key="${key}"]`;
 const bore=withStarts(s.nose.bore_segments),noseTotal=s.nose.visible_length_mm+s.nose.insertion_length_mm;
 const outerAt=x=>x<s.nose.visible_length_mm?s.nose.tip_diameter_mm+(s.nose.base_diameter_mm-s.nose.tip_diameter_mm)*x/s.nose.visible_length_mm:s.nose.insertion_diameter_mm;
 for(const issue of issues){
  if(issue==="Design name is required"){mark("#design-title",issue);continue}
  let match=issue.match(/^(Nose|Cap): (.+) must be positive$/);
  if(match){const keys=match[1]==="Nose"?noseKeys:capKeys,key=keys.find(item=>(names[item]||item)===match[2]);if(key)mark(match[1]==="Nose"?noseField(key):capField(key),issue);continue}
  if(issue==="Projection and clearances must be nonnegative"){
   for(const [id,value] of [["tip-projection",s.projection],["tip-clearance",s.tipClearance],["passage-clearance",s.passageClearance]])if(!Number.isFinite(value)||value<0)mark(`#${id}`,"Enter zero or a positive value.");
   continue;
  }
  if(issue==="Wood body dimensions must be positive"){
   if(!(s.bodyDiameter>0))mark("#body-diameter","Enter a positive outside diameter.");
   if(!(s.bodyLength>0))mark("#body-length","Enter a positive body length.");
   continue;
  }
  if(issue==="Nose insertion must be narrower than its base"){
   mark(noseField("insertion_diameter_mm"),"Reduce insertion diameter below the nose base diameter.");
   mark(noseField("base_diameter_mm"),"Increase the base diameter above the insertion diameter.");continue;
  }
  if(issue==="Cap insertion must be narrower than its outside"){
   mark(capField("insertion_diameter_mm"),"Reduce insertion diameter below the cap outside diameter.");
   mark(capField("diameter_mm"),"Increase the outside diameter above the insertion diameter.");continue;
  }
  if(issue==="Rounded edge radius exceeds the profile limit"){
   const noseLimit=Math.min(s.nose.tip_diameter_mm/4,s.nose.insertion_length_mm/2,s.nose.visible_length_mm/2);
   const capLimit=Math.min(s.cap.tip_diameter_mm/4,s.cap.insertion_length_mm/2,s.cap.length_mm/2);
   if(s.nose.round_radius_mm>=noseLimit)mark(noseField("round_radius_mm"),`Reduce this radius below ${noseLimit.toFixed(2)} mm.`);
   if(s.cap.round_radius_mm>=capLimit)mark(capField("round_radius_mm"),`Reduce this radius below ${capLimit.toFixed(2)} mm.`);
   continue;
  }
  if(issue==="Finish the partially entered bore row"||issue==="Nose bore needs at least one segment") {mark("#bore-segments",issue);continue}
  match=issue.match(/^Bore row (\d+): (.+)$/);
  if(match){
   const index=Number(match[1])-1,row=document.querySelectorAll("#bore-segments .designer__table-row")[index];
   if(match[2]==="less than 0.6 mm nose wall"){
    const seg=bore[index];if(!seg)continue;
    const positions=[seg.start_distance_mm,seg.end_distance_mm,Math.min(Math.max(s.nose.visible_length_mm,seg.start_distance_mm),seg.end_distance_mm)];
    const worst=positions.map(x=>({x,wall:(outerAt(x)-diameterAt(seg,x))/2})).sort((a,b)=>a.wall-b.wall)[0];
    const boreDiameter=diameterAt(seg,worst.x),neededOuter=boreDiameter+1.21;
    const inInsertion=worst.x>=s.nose.visible_length_mm;
    const fraction=worst.x/s.nose.visible_length_mm;
    const outerKey=inInsertion?"insertion_diameter_mm":fraction<0.5?"tip_diameter_mm":"base_diameter_mm";
    const coefficient=inInsertion?1:outerKey==="tip_diameter_mm"?1-fraction:fraction;
    const other=inInsertion?0:outerKey==="tip_diameter_mm"?s.nose.base_diameter_mm*fraction:s.nose.tip_diameter_mm*(1-fraction);
    const target=Math.ceil(((neededOuter-other)/coefficient)*100)/100;
    const wall=Number.isFinite(worst.wall)?worst.wall.toFixed(2):"unknown";
    const at=`at ${worst.x.toFixed(1)} mm from the nose tip`;
    const field=names[outerKey].toLowerCase();
    let action=`Increase nose ${field} to at least ${target.toFixed(2)} mm`;
    if(outerKey==="insertion_diameter_mm"&&target>=s.nose.base_diameter_mm)action+=`; base diameter must exceed ${target.toFixed(2)} mm`;
    if(outerKey==="insertion_diameter_mm"&&target+0.4>=s.bodyDiameter)action+=`; body outside diameter must exceed ${(target+0.4).toFixed(2)} mm`;
    const message=`Bore row ${index+1} leaves ${wall} mm of wall ${at}; 0.6 mm is required. ${action}.`;
    mark(noseField(outerKey),message);
    if(manualBore&&outerAt(worst.x)>1.21)mark(row,`Alternatively, reduce bore diameter ${at} below ${(outerAt(worst.x)-1.2).toFixed(2)} mm.`);
   }else mark(row,issue);
   continue;
  }
  if(issue==="Last bore end must equal nose visible plus insertion length"){
   mark(document.querySelectorAll("#bore-segments .designer__table-row").item(bore.length-1),`Set the final bore end to ${noseTotal.toFixed(1)} mm, or change the nose lengths.`);continue;
  }
  if(issue==="Body is too narrow for the insertion tube"){
   const minimum=Math.max(s.nose.insertion_diameter_mm,s.cap.insertion_diameter_mm)+0.4;
   mark("#body-diameter",`Increase outside diameter above ${minimum.toFixed(1)} mm to fit the insertion tube.`);continue;
  }
  if(issue==="Refill measurements are incomplete") {mark("#refill-filter","Choose a cartridge with complete dimensions.");continue}
  if(issue==="Refill intersects the nose bore"){
   if(manualBore)mark("#bore-segments","Enlarge the bore where it meets the refill, or change tip projection.");
   else mark("#passage-clearance","Increase passage clearance or change tip projection so the refill fits the bore.");
   continue;
  }
  if(issue.startsWith("Refill reaches the end cap")){mark("#body-length",issue);continue}
  if(issue==="Refill is wider than the body tube"){
   mark(noseField("insertion_diameter_mm"),"Increase the insertion tube diameters to clear the refill; the wood body may need to grow too.");
   mark(capField("insertion_diameter_mm"),"Increase the insertion tube diameters to clear the refill; the wood body may need to grow too.");continue;
  }
  mark(summary,issue);
 }
}
function xml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&apos;"})[c])}
function cutaway(s){
 const svg=$("cutaway"),parts=profile(s.refill),nose=s.nose,cap=s.cap;
 const noseEnd=nose.visible_length_mm,noseRear=noseEnd+nose.insertion_length_mm,bodyEnd=noseEnd+s.bodyLength;
 const total=Math.max(s.projection+bodyEnd+cap.length_mm,parts.at(-1)?.end_distance_mm||0,1);
 const scale=720/(total/Number($("cutaway-zoom").value)),x=v=>40+(v+s.projection)*scale;
 const largest=Math.max(s.bodyDiameter,nose.base_diameter_mm,nose.insertion_diameter_mm,cap.diameter_mm,cap.tip_diameter_mm,...parts.map(maxDiameter),1);
 const top=100,half=largest*scale/2,mid=top+half,rad=d=>Math.max(0.5,d*scale/2);
 svg.setAttribute("viewBox",`0 0 800 ${Math.ceil(mid+half+24)}`);
 const point=(a,r)=>`${x(a)},${mid-r}`;
 const polygon=(points,fill,stroke="none",opacity=1,attrs="")=>`<polygon points="${points.map(([a,r])=>point(a,r)).join(" ")}" fill="${fill}" stroke="${stroke}" opacity="${opacity}" ${attrs}/>`;
 let shapes=`<line x1="25" y1="${mid}" x2="780" y2="${mid}" stroke="#587391" stroke-dasharray="5 4"/>`;
 const tube=Math.max(nose.insertion_diameter_mm,cap.insertion_diameter_mm)+0.4;
 for(const sign of [-1,1]){
   shapes+=polygon([[noseEnd,sign*rad(s.bodyDiameter)],[bodyEnd,sign*rad(s.bodyDiameter)],[bodyEnd,sign*rad(tube)],[noseEnd,sign*rad(tube)]],"#8a5a36","#bd8a5d",.85,'data-section-kind="body" role="button" tabindex="0" aria-label="Body settings"');
 }
 const noseOuterAt=distance=>distance<noseEnd?nose.tip_diameter_mm+(nose.base_diameter_mm-nose.tip_diameter_mm)*distance/noseEnd:nose.insertion_diameter_mm;
 for(const [index,seg] of withStarts(nose.bore_segments).entries()){
   const start=seg.start_distance_mm,end=seg.end_distance_mm;
   const outer=[[start,noseOuterAt(start)]];
   if(start<noseEnd&&end>=noseEnd)outer.push([noseEnd,nose.base_diameter_mm],[noseEnd,nose.insertion_diameter_mm]);
   outer.push([end,noseOuterAt(end)]);
   const inner=[[end,diameterAt(seg,end)],[start,diameterAt(seg,start)]];
   const attrs=`data-section-kind="bore" data-section-index="${index}" role="button" tabindex="0" aria-label="Bore section ${index+1}, ending ${xml(end)} millimeters from the nose tip"`;
   for(const sign of [-1,1])shapes+=polygon([...outer,...inner].map(([a,d])=>[a,sign*rad(d)]),BORE_COLORS[index%BORE_COLORS.length],"#c6d8ed",.92,attrs);
 }
 const capInsertStart=bodyEnd-cap.insertion_length_mm;
 for(const sign of [-1,1])shapes+=polygon([[capInsertStart,sign*rad(cap.insertion_diameter_mm)],[bodyEnd,sign*rad(cap.insertion_diameter_mm)],[bodyEnd,sign*rad(cap.diameter_mm)],[bodyEnd+cap.length_mm,sign*rad(cap.tip_diameter_mm)],[bodyEnd+cap.length_mm,0],[capInsertStart,0]],"#8da9cd","#c6d8ed",.9,'data-section-kind="cap" role="button" tabindex="0" aria-label="End cap settings"');
 for(const [index,seg] of parts.entries()){
   const a=seg.start_distance_mm-s.projection,b=seg.end_distance_mm-s.projection;
   const start=seg.kind==="taper"?seg.diameter_start_mm:seg.diameter_mm,end=seg.kind==="taper"?seg.diameter_end_mm:seg.diameter_mm;
   const color=REFILL_COLORS[index%REFILL_COLORS.length];
   const attrs=`data-section-kind="refill" data-section-index="${index}" role="button" tabindex="0" aria-label="Refill section ${index+1}, ending ${xml(seg.end_distance_mm)} millimeters from the writing tip"`;
   shapes+=polygon([[a,-rad(start)],[b,-rad(end)],[b,rad(end)],[a,rad(start)]],color,"#fff1d8",1,attrs);
   const labelY=35+(index%3)*17;
   shapes+=`<line x1="${x(b)}" y1="${labelY+4}" x2="${x(b)}" y2="${top-9}" stroke="${color}"/><text x="${x(b)}" y="${labelY}" fill="${color}" font-size="11" text-anchor="middle">${xml(seg.end_distance_mm)} mm</text>`;
 }
 svg.innerHTML=shapes;applySelection();
 const overall=s.projection+noseEnd+s.bodyLength+cap.length_mm;
 const lengths=[["Projection",s.projection],["Nose",noseEnd],["Body",s.bodyLength],["Cap",cap.length_mm],["Overall",overall]];
 $("cutaway-dimensions").replaceChildren(...lengths.map(([label,value])=>{const item=document.createElement("span");item.className="designer__length";item.textContent=`${label} ${Number(value.toFixed(2))} mm`;return item}));
}
function overview(s){
 const svg=$("overview");if(!svg)return;
 const nose=s.nose,cap=s.cap,parts=profile(s.refill);
 const noseEnd=nose.visible_length_mm,bodyEnd=noseEnd+s.bodyLength,capEnd=bodyEnd+cap.length_mm;
 const left=Math.min(-s.projection,0),right=Math.max(capEnd,(parts.at(-1)?.end_distance_mm||0)-s.projection,1);
 const largest=Math.max(s.bodyDiameter,nose.base_diameter_mm,cap.diameter_mm,cap.tip_diameter_mm,...parts.map(maxDiameter),1);
 const scale=Math.min(744/Math.max(right-left,1),78/largest);
 const x=value=>(800-(right-left)*scale)/2+(value-left)*scale,mid=57,r=diameter=>Math.max(0,diameter)*scale/2;
 const p=(distance,diameter,sign)=>`${x(distance)},${mid+sign*r(diameter)}`;
 let shapes=`<line x1="24" y1="${mid}" x2="776" y2="${mid}" stroke="#587391" stroke-dasharray="5 4"/>`;
 shapes+=`<polygon points="${p(noseEnd,s.bodyDiameter,-1)} ${p(bodyEnd,s.bodyDiameter,-1)} ${p(bodyEnd,s.bodyDiameter,1)} ${p(noseEnd,s.bodyDiameter,1)}" fill="#8a5a36" stroke="#bd8a5d" data-section-kind="body" role="button" tabindex="0" aria-label="Body settings"/>`;
 shapes+=`<polygon points="${p(0,nose.tip_diameter_mm,-1)} ${p(noseEnd,nose.base_diameter_mm,-1)} ${p(noseEnd,nose.base_diameter_mm,1)} ${p(0,nose.tip_diameter_mm,1)}" fill="#8da9cd" stroke="#c6d8ed" data-section-kind="nose" role="button" tabindex="0" aria-label="Nose cone settings"/>`;
 shapes+=`<polygon points="${p(bodyEnd,cap.diameter_mm,-1)} ${p(capEnd,cap.tip_diameter_mm,-1)} ${p(capEnd,cap.tip_diameter_mm,1)} ${p(bodyEnd,cap.diameter_mm,1)}" fill="#8da9cd" stroke="#c6d8ed" data-section-kind="cap" role="button" tabindex="0" aria-label="End cap settings"/>`;
 for(const [index,seg] of parts.entries()){
  const start=seg.start_distance_mm-s.projection,end=seg.end_distance_mm-s.projection;
  const d1=seg.kind==="taper"?seg.diameter_start_mm:seg.diameter_mm,d2=seg.kind==="taper"?seg.diameter_end_mm:seg.diameter_mm;
  shapes+=`<polygon points="${p(start,d1,-1)} ${p(end,d2,-1)} ${p(end,d2,1)} ${p(start,d1,1)}" fill="${REFILL_COLORS[index%REFILL_COLORS.length]}" stroke="#fff1d8" data-section-kind="refill" data-section-index="${index}" role="button" tabindex="0" aria-label="Refill section ${index+1} settings"/>`;
 }
 shapes+=`<text x="${x((noseEnd)/2)}" y="118" fill="#bccde4" font-size="11" text-anchor="middle">Nose ${xml(nose.visible_length_mm)} mm</text>`;
 shapes+=`<text x="${x((noseEnd+bodyEnd)/2)}" y="118" fill="#d8b793" font-size="11" text-anchor="middle">Body ${xml(s.bodyLength)} mm</text>`;
 shapes+=`<text x="${x(capEnd)}" y="118" fill="#bccde4" font-size="11" text-anchor="end">Cap ${xml(cap.length_mm)} mm</text>`;
 svg.innerHTML=shapes;
}
function cylinder(T,scene,d1,d2,length,start,color,opacity=1){if(length<=0)return;const geo=new T.CylinderGeometry(d2/2,d1/2,length,48);const mat=new T.MeshStandardMaterial({color,transparent:opacity<1,opacity,side:T.DoubleSide,metalness:.13,roughness:.52});const mesh=new T.Mesh(geo,mat);mesh.position.y=start+length/2;scene.add(mesh)}
async function initThree(){try{const {THREE:T,OrbitControls}=await ensureViewerModules();const container=$("assembly"),scene=new T.Scene();scene.background=new T.Color(0x07090f);const camera=new T.PerspectiveCamera(40,1,.1,1000),renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));container.append(renderer.domElement);scene.add(new T.HemisphereLight(0xffffff,0x25354b,2));const light=new T.DirectionalLight(0xffffff,1.7);light.position.set(20,30,30);scene.add(light);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;let parts=[];function renderState(s){for(const obj of parts){scene.remove(obj);obj.geometry.dispose();obj.material.dispose()}parts=[];const old=new Set(scene.children);cylinder(T,scene,s.nose.tip_diameter_mm,s.nose.base_diameter_mm,s.nose.visible_length_mm,0,0x9bb8dc);cylinder(T,scene,s.bodyDiameter,s.bodyDiameter,s.bodyLength,s.nose.visible_length_mm,0x9b673f,.55);cylinder(T,scene,s.cap.diameter_mm,s.cap.tip_diameter_mm,s.cap.length_mm,s.nose.visible_length_mm+s.bodyLength,0x9bb8dc);for(const [index,seg] of profile(s.refill).entries())cylinder(T,scene,seg.kind==="taper"?seg.diameter_start_mm:seg.diameter_mm,seg.kind==="taper"?seg.diameter_end_mm:seg.diameter_mm,seg.end_distance_mm-seg.start_distance_mm,seg.start_distance_mm-s.projection,parseInt(REFILL_COLORS[index%REFILL_COLORS.length].slice(1),16));parts=[...scene.children].filter(o=>!old.has(o));const total=s.nose.visible_length_mm+s.bodyLength+s.cap.length_mm;camera.position.set(Math.max(total*1.7,55),total*.8,Math.max(total*1.7,55));controls.target.set(0,total/2,0);controls.update()}
 function resize(){const w=container.clientWidth,h=container.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix()}new ResizeObserver(resize).observe(container);resize();function loop(){requestAnimationFrame(loop);controls.update();renderer.render(scene,camera)}loop();three=renderState;update()}catch(e){$("assembly-status").textContent=`3D preview unavailable: ${e.message}`}}
function yaml(value,depth=0){const pad="  ".repeat(depth);if(Array.isArray(value))return value.map(item=>`${pad}- ${typeof item==="object"&&item!==null?"\n"+yaml(item,depth+1):JSON.stringify(item)}`).join("\n");if(value&&typeof value==="object")return Object.entries(value).map(([k,v])=>`${pad}${k}:${v&&typeof v==="object"?"\n"+yaml(v,depth+1):` ${JSON.stringify(v)}`}`).join("\n");return `${pad}${JSON.stringify(value)}`}
function download(filename,contents){const link=document.createElement("a"),url=URL.createObjectURL(new Blob([contents],{type:"text/yaml"}));link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function githubLink(anchor,path,contents){const url=`https://github.com/jquintus/pens/new/main?filename=${encodeURIComponent(path)}&value=${encodeURIComponent(contents)}`;if(url.length<7000){anchor.href=url;anchor.removeAttribute("aria-disabled");anchor.title=""}else{anchor.removeAttribute("href");anchor.setAttribute("aria-disabled","true");anchor.title="File is too large for a prefilled URL; use Download"}}
function configYaml(s){const copy=structuredClone(currentPen.config),first=s.nose.bore_segments[0],last=s.nose.bore_segments.at(-1);copy.id=s.designId;copy.title=s.designTitle;copy.nose_cone={cylinder_height:s.nose.insertion_length_mm,cylinder_outside_diameter:s.nose.insertion_diameter_mm,frustum_height:s.nose.visible_length_mm,frustum_top_diameter:s.nose.tip_diameter_mm,frustum_bottom_diameter:s.nose.base_diameter_mm,top_hole_diameter:first?.kind==="taper"?first.diameter_start_mm:first?.diameter_mm??s.nose.stop_diameter_mm,bottom_hole_diameter:last?.kind==="taper"?last.diameter_end_mm:last?.diameter_mm??s.nose.passage_diameter_mm,top_hole_height:first?.end_distance_mm??s.nose.stop_depth_mm};if(s.refill)copy.refill=s.refill.id;else delete copy.refill;copy.openscad={nose_cone:s.nose,end_cap:s.cap,refill_tip_projection_mm:s.projection,refill_tip_clearance_mm:s.tipClearance,refill_passage_clearance_mm:s.passageClearance};return yaml(copy)+"\n"}
function scadSource(s){const fields={nose_cone:s.nose,end_cap:s.cap}, assignments=Object.entries(fields).flatMap(([section,values])=>Object.entries(values).map(([key,value])=>`${section}_${key} = ${key==="bore_segments"?JSON.stringify(value.map(seg=>seg.kind==="taper"?[seg.diameter_start_mm,seg.diameter_end_mm,seg.end_distance_mm]:[seg.diameter_mm,seg.diameter_mm,seg.end_distance_mm])):value};`));const args=Object.entries(fields).flatMap(([section,values])=>Object.keys(values).map(key=>`${section}_${key}=${section}_${key}`));return `// Self-contained OpenSCAD source. Dimensions in millimeters.\n${assignments.join("\n")}\n$fn = 128;\n\n${data.scad_module}\ndesigner_parts(${args.join(", ")});\n`}
function refillForExport(){if(!currentRefill)return null;const copy=structuredClone(currentRefill);delete copy.geometry_ready;delete copy.overall_length_mm;return copy}
function showRefill(){const r=currentRefill;selectedSection=null;for(const [key,id] of [["id","refill-id"],["brand","refill-brand"],["model","refill-model"],["format","refill-format"],["measurement_status","refill-status"],["ink_type","refill-ink"]])$(id).value=r?.[key]||"";refillDraftError=false;renderRefillDimensions(r?.segments||[]);$("view-cartridge").href=r?`cartridges.html?id=${encodeURIComponent(r.id)}`:"cartridges.html";$("refill-info").textContent=r?`${r.format} · ${r.measurement_status} · ${r.segments?.at(-1)?.end_distance_mm??"unknown"} mm total`:"Select a refill to check its clearance and display its measured shape.";update()}
function update(){if(!currentPen)return;const s=getState(),issues=validate(s);const halfAngle=Math.atan((s.nose.base_diameter_mm-s.nose.tip_diameter_mm)/(2*s.nose.visible_length_mm))*180/Math.PI;$("nose-angle").textContent=Number.isFinite(halfAngle)?`Outer taper: ${Math.abs(halfAngle).toFixed(1)}° from axis · ${(2*Math.abs(halfAngle)).toFixed(1)}° included`:"Outer taper angle unavailable";renderValidation(s,issues);overview(s);cutaway(s);if(three)three(s);const valid=!issues.length;$("download-config").disabled=!valid;$("download-scad").disabled=!valid;const text=configYaml(s),path=`configurations/${s.designId}.yml`;if(valid)githubLink($("github-config"),path,text);else{$("github-config").removeAttribute("href");$("github-config").setAttribute("aria-disabled","true")}
 const refill=refillForExport(),refillErrors=refillIssues(refill);$("download-refill").disabled=!!refillErrors.length;if(!refillErrors.length)githubLink($("github-refill"),`refills/${refill.id}.yml`,yaml(refill)+"\n");else{$("github-refill").removeAttribute("href");$("github-refill").setAttribute("aria-disabled","true");$("github-refill").title=refillErrors.join(" · ")}}
const penTitleCounts=new Map();for(const pen of data.pens){const title=pen.config.title||pen.id;penTitleCounts.set(title,(penTitleCounts.get(title)||0)+1)}
const penChoices=[{value:"new",label:"New design"},...data.pens.map(p=>{const title=p.config.title||p.id,diameter=p.config.nose_cone?.cylinder_outside_diameter;return {value:p.id,label:penTitleCounts.get(title)>1&&Number.isFinite(diameter)?`${title} · ${diameter.toFixed(2)} mm insertion`:title}})];
const refillChoices=[{value:"",label:"No refill selected"},...data.refills.map(r=>({value:r.id,label:`${r.brand} ${r.model}${r.measurement_status==="incomplete"?" (incomplete)":""}`,search:(r.source_pens||[]).join(" ")}))];
function matchesChoice(choice,query){const normalize=value=>String(value).toLowerCase().replace(/[^a-z0-9]+/g," ").trim().replace(/\s+/g," ");return normalize(`${choice.label} ${choice.value} ${choice.search||""}`).includes(normalize(query))}
function selectedLabel(selectId,choices){return choices.find(choice=>choice.value===$(selectId).value)?.label||""}
function syncCombo(inputId,selectId,choices){$(inputId).value=selectedLabel(selectId,choices)}
function bindCombobox(inputId,selectId,listId,choices){
 const input=$(inputId),select=$(selectId),list=$(listId);let matches=[],active=-1;
 function setActive(index){active=index;for(const [i,option] of [...list.children].entries())option.setAttribute("aria-selected",String(i===active));if(active>=0){input.setAttribute("aria-activedescendant",`${listId}-${active}`);list.children[active]?.scrollIntoView({block:"nearest"})}else input.removeAttribute("aria-activedescendant")}
 function render(query){matches=choices.filter(choice=>matchesChoice(choice,query));list.replaceChildren();for(const [index,choice] of matches.entries()){const option=document.createElement("div");option.id=`${listId}-${index}`;option.className="designer__combo-option";option.role="option";option.textContent=choice.label;option.setAttribute("aria-selected","false");option.addEventListener("pointerdown",event=>event.preventDefault());option.addEventListener("click",()=>commit(choice));list.append(option)}if(!matches.length){const empty=document.createElement("div");empty.className="designer__combo-empty";empty.textContent="No matches";list.append(empty)}setActive(-1)}
 function open(query=""){render(query);list.hidden=false;input.setAttribute("aria-expanded","true")}
 function close(restore=true){list.hidden=true;input.setAttribute("aria-expanded","false");input.removeAttribute("aria-activedescendant");if(restore)syncCombo(inputId,selectId,choices)}
 function commit(choice){select.value=choice.value;close(false);input.value=choice.label;select.dispatchEvent(new Event("change",{bubbles:true}))}
 input.addEventListener("focus",()=>{input.select();open()});
 input.addEventListener("input",()=>open(input.value));
 input.addEventListener("keydown",event=>{if(event.key==="ArrowDown"||event.key==="ArrowUp"){event.preventDefault();if(list.hidden)open();if(matches.length)setActive(active<0?(event.key==="ArrowDown"?0:matches.length-1):(active+(event.key==="ArrowDown"?1:-1)+matches.length)%matches.length);return}if(event.key==="Enter"){if(!list.hidden&&matches.length){event.preventDefault();commit(matches[active>=0?active:0])}return}if(event.key==="Escape"){event.preventDefault();close();return}if(event.key==="Tab"&& !list.hidden){if(input.value!==selectedLabel(selectId,choices)&&matches.length)commit(matches[active>=0?active:0]);else close()}});
 input.addEventListener("blur",()=>setTimeout(()=>close(),0));
 const toggle=input.parentElement.querySelector(".designer__combo-toggle");
 toggle.addEventListener("pointerdown",event=>event.preventDefault());
 toggle.addEventListener("click",()=>{input.focus();input.select();open()});
 select.addEventListener("change",()=>syncCombo(inputId,selectId,choices));
 syncCombo(inputId,selectId,choices);
}
for(const choice of penChoices)option($("pen-select"),choice.value,choice.label);
for(const choice of refillChoices)option($("refill-select"),choice.value,choice.label);
bindCombobox("pen-filter","pen-select","pen-options",penChoices);
bindCombobox("refill-filter","refill-select","refill-options",refillChoices);
const designNonce=Date.now().toString(36);
function setNumber(id,value){$(id).value=value;$(id).nextElementSibling.value=value}
function newDesignGeometry(refill){
 const parts=profile(refill),projection=parts[0]?.end_distance_mm??0,visible=12,insertionLength=5;
 const largest=parts.length?Math.max(...parts.map(maxDiameter)):5;
 let body=Math.max(7,Math.ceil(largest+2.6)),tip=2.5,bore=[];
 for(let attempt=0;attempt<40;attempt++){
  const base=body-0.1,insertion=body-0.7;
  bore=deriveBore(refill,projection,0.3,0.4,visible+insertionLength)||[];
  tip=2.5;
  for(const segment of withStarts(bore))for(const distance of [segment.start_distance_mm,segment.end_distance_mm])if(distance<visible){const t=distance/visible;tip=Math.max(tip,(diameterAt(segment,distance)+1.25-base*t)/(1-t))}
  tip=Math.ceil(tip*10)/10;
  if(tip<=base-0.3&&bore.every((segment,index)=>{const start=index?bore[index-1].end_distance_mm:0;return start<visible||insertion>maxDiameter(segment)+1.2}))break;
  body++;
 }
 const base=body-0.1,insertion=body-0.7;
 const nose={...defaults.nose_cone,visible_length_mm:visible,insertion_length_mm:insertionLength,insertion_diameter_mm:insertion,base_diameter_mm:base,tip_diameter_mm:tip,round_radius_mm:0.3};
 const cap={...defaults.end_cap,length_mm:2,diameter_mm:base,tip_diameter_mm:insertion,insertion_length_mm:insertionLength,insertion_diameter_mm:insertion,round_radius_mm:0.3};
 const length=Math.max(40,Math.ceil(((parts.at(-1)?.end_distance_mm??100)-projection-visible+insertionLength+1)*10)/10);
 return {nose,cap,body,length,projection};
}
function choosePen(){
 const isNew=$("pen-select").value==="new";
 currentPen=isNew?{id:`design-${currentRefill?.id||"refill"}-${designNonce}`,config:{slicing_profiles:["0.2_fast","0.2_quality"]}}:data.pens.find(p=>p.id===$("pen-select").value);
 const legacy=currentPen.config.nose_cone||{},override=currentPen.config.openscad||{};
 const fresh=isNew?newDesignGeometry(currentRefill):null;
 const nose=isNew?fresh.nose:{...defaults.nose_cone,visible_length_mm:legacy.frustum_height,insertion_length_mm:legacy.cylinder_height,insertion_diameter_mm:legacy.cylinder_outside_diameter,base_diameter_mm:legacy.frustum_bottom_diameter,tip_diameter_mm:legacy.frustum_top_diameter,passage_diameter_mm:legacy.bottom_hole_diameter,stop_diameter_mm:legacy.top_hole_diameter,stop_depth_mm:legacy.top_hole_height,...override.nose_cone};
 const cap=isNew?fresh.cap:{...defaults.end_cap,diameter_mm:legacy.frustum_bottom_diameter,tip_diameter_mm:legacy.cylinder_outside_diameter,insertion_length_mm:legacy.cylinder_height,insertion_diameter_mm:legacy.cylinder_outside_diameter,...override.end_cap};
 $("design-title").value=isNew?`Pen for ${currentRefill?.brand||"refill"} ${currentRefill?.model||""}`.trim():currentPen.config.title||currentPen.id;
 baseNose=nose;manualBore=!isNew&&!!override.nose_cone?.bore_segments;currentBore=structuredClone(override.nose_cone?.bore_segments||[]);boreHash="";boreDraftError=false;
 projectionCustomized=!isNew&&override.refill_tip_projection_mm!==undefined;
 setNumber("tip-clearance",isNew?0.3:override.refill_tip_clearance_mm??0.3);
 setNumber("passage-clearance",isNew?0.4:override.refill_passage_clearance_mm??0.4);
 numericFields($("nose-fields"),noseKeys,nose);numericFields($("cap-fields"),capKeys,cap);
 if(manualBore)renderBore();
 setProjectionDefault(currentRefill,isNew?fresh.projection:override.refill_tip_projection_mm);
 if(isNew){setNumber("body-diameter",fresh.body);setNumber("body-length",fresh.length)}
 else if(currentRefill?.overall_length_mm){const minimum=Math.ceil((currentRefill.overall_length_mm-Number($("tip-projection").value)-nose.visible_length_mm+cap.insertion_length_mm+0.1)*10)/10;if(minimum>Number($("body-length").value))setNumber("body-length",minimum)}
 showRefill();
}
function showDiagram(view){for(const name of ["overview","cutaway"]){$(name+"-panel").hidden=name!==view;$("show-"+name).setAttribute("aria-selected",String(name===view))}}
$("show-overview").addEventListener("click",()=>showDiagram("overview"));
$("show-cutaway").addEventListener("click",()=>showDiagram("cutaway"));
for(const id of ["cutaway","overview"]){$(id).addEventListener("click",event=>{const section=event.target.closest?.("[data-section-kind]");if(section)selectSection(section.dataset.sectionKind,section.dataset.sectionIndex===undefined?undefined:Number(section.dataset.sectionIndex),true)});$(id).addEventListener("keydown",event=>{if(event.key!=="Enter"&&event.key!==" ")return;const section=event.target.closest?.("[data-section-kind]");if(section){event.preventDefault();selectSection(section.dataset.sectionKind,section.dataset.sectionIndex===undefined?undefined:Number(section.dataset.sectionIndex),true)}})}
for(const id of ["segments","bore-segments"])$(id).addEventListener("click",event=>{const row=event.target.closest?.(".designer__table-row[data-section-index]");if(row)selectSection(row.dataset.sectionKind,Number(row.dataset.sectionIndex))});
$("cutaway-zoom").addEventListener("input",()=>{$("cutaway-zoom-value").textContent=`${$("cutaway-zoom").value}×`;update()});$("pen-select").addEventListener("change",choosePen);$("refill-select").addEventListener("change",()=>{currentRefill=$("refill-select").value==="new"?{id:"",brand:"",model:"",format:"",measurement_status:"incomplete",segments:[],geometry_ready:false}:data.refills.find(r=>r.id===$("refill-select").value);projectionCustomized=false;if($("pen-select").value==="new")choosePen();else{setProjectionDefault(currentRefill);showRefill()}});for(const [id,max,step] of [["body-diameter",35,.1],["body-length",200,.5],["tip-projection",15,.1],["tip-clearance",3,.05],["passage-clearance",3,.05]])attachSlider(id,max,step);for(const [key,id] of [["id","refill-id"],["brand","refill-brand"],["model","refill-model"],["format","refill-format"],["measurement_status","refill-status"],["ink_type","refill-ink"]])$(id).addEventListener("input",()=>{if(!currentRefill)currentRefill={id:"",brand:"",model:"",format:"",measurement_status:"incomplete",segments:[]};currentRefill[key]=$(id).value;currentRefill.geometry_ready=currentRefill.measurement_status!=="incomplete"&&!refillIssues(currentRefill).length;update()});$("customize-bore").addEventListener("click",()=>{manualBore=true;renderBore();update()});$("reset-bore").addEventListener("click",()=>{manualBore=false;boreDraftError=false;boreHash="";update()});$("download-config").addEventListener("click",()=>download(`configurations-${getState().designId}.yml`,configYaml(getState())));$("download-scad").addEventListener("click",()=>download(`${getState().designId}.scad`,scadSource(getState())));$("download-refill").addEventListener("click",()=>{const r=refillForExport();if(r)download(`refills-${r.id}.yml`,yaml(r)+"\n")});$("refill-select").value=(data.refills.some(r=>r.id===initialRefill)?initialRefill:data.refills.find(r=>r.geometry_ready)?.id)||"";currentRefill=data.refills.find(r=>r.id===$("refill-select").value);syncCombo("refill-filter","refill-select",refillChoices);$("design-title").addEventListener("input",update);choosePen();
