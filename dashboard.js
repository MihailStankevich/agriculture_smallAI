const $ = id => document.getElementById(id);
const COFFEE_LABELS = new Set(["Cerscospora", "Healthy", "Leaf_rust", "Miner", "Phoma"]);
const prettyLabel = label => ({Cerscospora:"Coffee — Cercospora leaf spot",Healthy:"Coffee — no visible supported condition",Leaf_rust:"Coffee — leaf rust",Miner:"Coffee — leaf miner",Phoma:"Coffee — Phoma leaf spot"}[label] || label);
const observationText = {spreading:"marks spreading",wet:"wet leaf/field","many-plants":"more than one plant",underside:"marks under leaf"};
let state = {reports:[], outbreaks:[], rules:{radiusKm:12}};

function toast(message) { const node=$("toast"); node.textContent=message; node.classList.add("show"); setTimeout(()=>node.classList.remove("show"),2800); }
async function request(path, options) { const response=await fetch(path, options); if(!response.ok) throw new Error("Request failed"); return response.json(); }
function coffeeOnly(items) { return items.filter(item=>COFFEE_LABELS.has(item.label)); }
function signalAge(iso) { const hours=Math.max(0, Math.round((Date.now()-new Date(iso))/36e5)); return hours<1?"just now":hours<24?`${hours}h ago`:`${Math.round(hours/24)}d ago`; }
function observations(list=[]) { const words=list.map(item=>observationText[item]).filter(Boolean); return words.length?words.join(" · "):"No field observations selected"; }
function alertMessage(outbreak) { return `Tahadhari ya CropSignal: kuna ripoti ${outbreak.count} za ${prettyLabel(outbreak.label)} ndani ya kilomita ${outbreak.radiusKm} katika siku 7. Dalili zilizoripotiwa: ${observations(outbreak.observations)}. Hii si uthibitisho wa ugonjwa. Afisa wa ugani athibitishe kabla ya kutuma ushauri wa matibabu.`; }

async function refresh() {
  try {
    const [reports, outbreaks] = await Promise.all([request("/api/reports"), request("/api/outbreaks")]);
    state = {reports:coffeeOnly(reports.reports), outbreaks:coffeeOnly(outbreaks.outbreaks), rules:outbreaks.rules}; render();
  } catch { toast("Dashboard needs the local CropSignal server."); }
}
function renderAlert(outbreak, index) {
  const urgency=outbreak.label==="Leaf_rust"?"Priority field check":"Field check needed";
  return `<article class="alert"><div class="alert-head"><span class="alert-status">${urgency}</span><span>${outbreak.count} matching signals</span></div><strong>${prettyLabel(outbreak.label)}</strong><p><b>Why this is here:</b> ${outbreak.count} matching signals were received within ${outbreak.radiusKm} km in the last ${outbreak.windowDays} days. Average model confidence: ${Math.round(outbreak.averageConfidence*100)}%.</p><p><b>What farmers observed:</b> ${observations(outbreak.observations)}.</p><div class="next-action"><b>Extension next step</b><span>Visit the rounded zone, inspect at least five coffee plants, and confirm before sharing treatment advice or community messages.</span></div><button class="button secondary draft-alert" data-index="${index}">View Kiswahili message draft</button><p class="alert-copy" id="alert-copy-${index}" hidden></p></article>`;
}
function render() {
  $("reportMetric").textContent=state.reports.length; $("outbreakMetric").textContent=state.outbreaks.length; $("coverageMetric").textContent=`${state.rules.radiusKm} km`;
  const alerts=$("outbreakList"); alerts.innerHTML=state.outbreaks.length?state.outbreaks.map(renderAlert).join(""):'<p class="empty">No coffee cluster needs a visit yet. This is expected until five similar local signals arrive within seven days.</p>';
  document.querySelectorAll(".draft-alert").forEach(button=>button.addEventListener("click",()=>{const index=Number(button.dataset.index),copy=$("alert-copy-"+index);copy.textContent=alertMessage(state.outbreaks[index]);copy.hidden=false;button.textContent="Draft shown — review before sending";}));
  const reports=$("reportList"); reports.innerHTML=state.reports.length?state.reports.slice().reverse().slice(0,8).map(report=>`<div class="report"><div><b>${prettyLabel(report.label)}</b><small>${observations(report.observations)} · ${signalAge(report.createdAt)}</small></div><span>${Math.round(report.confidence*100)}%</span></div>`).join(""):'<p class="empty">No coffee signals received yet. Use “Show coffee-rust demo” to see the full workflow.</p>'; drawMap();
}
let leaflet = null, layer = null, fitted = false;
function drawRealMap() {
  if (!leaflet) {
    leaflet = L.map("realmap", {zoomControl:true, scrollWheelZoom:false}).setView([-1.29, 36.82], 11);
    const street = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom:19, attribution:"© OpenStreetMap"});
    const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {maxZoom:19, attribution:"Imagery © Esri"});
    satellite.addTo(leaflet); L.control.layers({"Satellite":satellite, "Street":street}).addTo(leaflet);
    layer = L.layerGroup().addTo(leaflet);
  }
  layer.clearLayers();
  state.outbreaks.forEach(o => {
    L.circle([o.lat, o.lon], {radius:o.radiusKm*1000, color:"#ff5a4a", weight:2, dashArray:"6 6", fillColor:"#ff5a4a", fillOpacity:.2}).addTo(layer)
      .bindTooltip("VERIFY THIS ZONE · "+o.count+" signals", {permanent:true, direction:"top"});
  });
  state.reports.forEach(r => L.circleMarker([r.lat, r.lon], {radius:7, color:"#fff", weight:2, fillColor:"#1fa66a", fillOpacity:1}).addTo(layer)
    .bindPopup(`<b>${prettyLabel(r.label)}</b><br>${Math.round(r.confidence*100)}% · ${signalAge(r.createdAt)}`));
  if (state.reports.length && !fitted) { leaflet.fitBounds(L.latLngBounds(state.reports.map(r=>[r.lat,r.lon])).pad(.6)); fitted = true; }
  setTimeout(() => leaflet.invalidateSize(), 0);
}
function drawMap() {
  if (window.L) { try { return drawRealMap(); } catch (e) { console.error(e); } }
  $("realmap").hidden = true; $("map").hidden = false;
  const canvas=$("map"), context=canvas.getContext("2d"), rect=canvas.getBoundingClientRect(), dpr=devicePixelRatio||1;
  canvas.width=rect.width*dpr; canvas.height=rect.height*dpr; context.scale(dpr,dpr); const width=rect.width,height=rect.height;
  context.fillStyle="#dfeee2"; context.fillRect(0,0,width,height);
  for(let i=0;i<12;i++){context.strokeStyle="#c6ddca";context.lineWidth=1;context.beginPath();context.moveTo(i*width/11,0);context.lineTo(i*width/11,height);context.stroke();context.beginPath();context.moveTo(0,i*height/11);context.lineTo(width,i*height/11);context.stroke();}
  if(!state.reports.length){context.fillStyle="#527464";context.textAlign="center";context.font="600 15px system-ui";context.fillText("Waiting for anonymous coffee signals",width/2,height/2);return;}
  const lats=state.reports.map(report=>report.lat), lons=state.reports.map(report=>report.lon), minLat=Math.min(...lats)-.1,maxLat=Math.max(...lats)+.1,minLon=Math.min(...lons)-.1,maxLon=Math.max(...lons)+.1;
  const point=record=>({x:44+(record.lon-minLon)/(maxLon-minLon||1)*(width-88),y:height-44-(record.lat-minLat)/(maxLat-minLat||1)*(height-88)});
  state.outbreaks.forEach(outbreak=>{const p=point(outbreak),radius=Math.min(width,height)*.15;context.beginPath();context.arc(p.x,p.y,radius,0,Math.PI*2);context.fillStyle="#d94b3d22";context.fill();context.strokeStyle="#d94b3d";context.setLineDash([6,5]);context.stroke();context.setLineDash([]);context.fillStyle="#a52c22";context.font="700 12px system-ui";context.textAlign="center";context.fillText("VERIFY THIS ZONE",p.x,p.y-radius-8);});
  state.reports.forEach(report=>{const p=point(report);context.beginPath();context.arc(p.x,p.y,6,0,Math.PI*2);context.fillStyle="#145e3d";context.fill();context.strokeStyle="white";context.lineWidth=2;context.stroke();});
}
$("seedBtn").addEventListener("click",async()=>{try{await request("/api/seed",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});await refresh();announceOutbreak();}catch{toast("Could not load the coffee demo.");}});
function announceOutbreak() {
  const outbreak=state.outbreaks[0]; if(!outbreak) return toast("Demo loaded, but no zone met the threshold.");
  const banner=$("alertBanner"); banner.querySelector("span").textContent=`${outbreak.count} signals of ${prettyLabel(outbreak.label)} within ${outbreak.radiusKm} km — verify this zone first.`;
  banner.classList.add("show"); setTimeout(()=>banner.classList.remove("show"),7000);
  if(leaflet) leaflet.flyTo([outbreak.lat,outbreak.lon],12,{duration:1.6});
  const card=document.querySelector(".alert"); if(card){card.scrollIntoView({behavior:"smooth",block:"center"});card.classList.add("pulse");setTimeout(()=>card.classList.remove("pulse"),4000);}
}
window.addEventListener("resize",drawMap); refresh(); setInterval(refresh,15000);
