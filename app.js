const storeKey = "cropsignal-pending-reports";
let demoLocationEnabled = false, currentLocation = null, savedCurrent = false;
let classifier = null, labels = [], currentResult = null;
const $ = id => document.getElementById(id);
const getQueue = () => JSON.parse(localStorage.getItem(storeKey) || "[]");
const setQueue = value => localStorage.setItem(storeKey, JSON.stringify(value));
const toast = message => { const node=$("toast"); node.textContent=message; node.classList.add("show"); setTimeout(()=>node.classList.remove("show"),3000); };
const swahili = {
  uncertain: "Matokeo hayana uhakika. Kagua majani matano ya mmea huu na mimea iliyo karibu. Angalia kama alama zinaenea na piga picha ya jani moja kwenye mwanga mzuri. Usinyunyize dawa wala kutuma ripoti ya jamii kutokana na matokeo haya pekee.",
  safe: "Hii ni ishara ya awali, si utambuzi wa ugonjwa. Usinyunyize dawa kwa msingi wa skrini hii pekee. Wasiliana na afisa wa ugani kwa uthibitisho.",
  action: "Chukua hatua sasa",
  monitor: "Fuatilia",
  avoid: "Epuka",
  sms: "Ripoti ya CropSignal"
};

function displayLabel(label) { const coffee={Cerscospora:"Coffee — Cercospora leaf spot",Healthy:"Coffee — no visible supported condition",Leaf_rust:"Coffee — leaf rust",Miner:"Coffee — leaf miner",Phoma:"Coffee — Phoma leaf spot"}; return coffee[label] || label.replace(/___/g, " — ").replace(/_/g, " ").replace(/\s+/g," ").trim(); }
function cropForLabel() { return "coffee"; }
function predictionTensor(value) {
  if (value instanceof tf.Tensor) return value;
  if (Array.isArray(value)) return value[0];
  return Object.values(value)[0];
}
function guidance(label) {
  return window.CROP_KNOWLEDGE?.[label] || {action:"Take a close photo of one leaf and mark the plant for follow-up.",monitor:"Compare several leaves and record whether symptoms are spreading.",avoid:"Do not make a treatment decision from this screen alone."};
}
function selectedObservations() { return [...document.querySelectorAll('input[name="observation"]:checked')].map(item=>item.value); }
function isSwahili() { return $("languageSelect")?.value === "sw"; }
function renderGuidance(label) {
  const item=guidance(label), node=$("advice");
  if (isSwahili()) node.innerHTML=`<b>${swahili.action}:</b> Kagua jani hili na mimea ya jirani, kisha weka alama kwenye mmea unaoshukiwa.<br><b>${swahili.monitor}:</b> Angalia kama alama zinaenea baada ya mvua au unyevunyevu.<br><b>${swahili.avoid}:</b> ${swahili.safe}`;
  else node.innerHTML=`<b>Do now:</b> ${item.action}<br><b>Monitor:</b> ${item.monitor}<br><b>Avoid:</b> ${item.avoid}`;
}
function adviceForVoice() {
  if (!currentResult) return "Analyze a crop leaf before requesting guidance.";
  if (currentResult.uncertain) return isSwahili() ? swahili.uncertain : "The result is uncertain. Inspect five leaves on this plant and nearby plants. Check whether marks are spreading and photograph one leaf in good light. Do not spray or share a community report from this result.";
  if (isSwahili()) return `${swahili.action}. Kagua jani hili na mimea ya jirani, kisha weka alama kwenye mmea unaoshukiwa. ${swahili.monitor}. Angalia kama alama zinaenea baada ya mvua au unyevunyevu. ${swahili.avoid}. ${swahili.safe}`;
  const item=guidance(currentResult.label);
  return `CropSignal guidance. ${displayLabel(currentResult.label)}. Do now: ${item.action}. Monitor: ${item.monitor}. Avoid: ${item.avoid}`;
}
let voiceAudio = null;
async function playAudio(source) {
  if (voiceAudio) voiceAudio.pause();
  voiceAudio = new Audio(source); await voiceAudio.play();
}
async function speakAdvice() {
  // 1) live ElevenLabs voice via the local server (key never reaches the phone),
  // 2) bundled pre-generated Kiswahili clips (offline), 3) installed device voice.
  const text = adviceForVoice(), button = $("speakBtn");
  if (navigator.onLine) {
    button.disabled = true; button.textContent = "Generating voice…";
    try {
      const response = await fetch("/api/tts", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text})});
      if (response.ok) { const url = URL.createObjectURL(await response.blob()); await playAudio(url); return; }
    } catch (_) { /* fall through to bundled clip */ }
    finally { button.disabled = false; button.textContent = "▶ Hear guidance"; }
  }
  const clip = isSwahili() && currentResult ? (currentResult.uncertain ? "/audio/uncertain-sw.mp3" : currentResult.label === "Leaf_rust" ? "/audio/coffee-rust-sw.mp3" : null) : null;
  if (clip) {
    try { await playAudio(clip); return; } catch (_) { /* fall through to installed device voice */ }
  }
  if (!("speechSynthesis" in window)) return toast("This phone does not provide a device voice.");
  window.speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(text);
  utterance.lang=isSwahili()?"sw-KE":"en-KE"; utterance.rate=.9;
  window.speechSynthesis.speak(utterance);
}
function composeSms() {
  if (!currentResult) return toast("Analyze a crop leaf before preparing an SMS.");
  const number=$("smsNumber").value.trim().replace(/[^+\d]/g,"");
  const crop="Arabica coffee";
  const status=currentResult.uncertain?"REVIEW NEEDED":"FIELD SIGNAL";
  const context=selectedObservations().join(", ") || "no symptoms selected";
  const message=isSwahili()?`${swahili.sms}: ${crop}; ${displayLabel(currentResult.label)}; uhakika ${Math.round(currentResult.confidence*100)}%; dalili: ${context}. Hakuna picha au jina.`:`CropSignal ${status}: ${crop}; ${displayLabel(currentResult.label)}; confidence ${Math.round(currentResult.confidence*100)}%; signs: ${context}. No photo or name shared.`;
  // Desktop browsers have no sms: handler (this used to fail with an error page),
  // so always show the drafted message and only offer the phone action on mobile.
  $("smsPreviewText").textContent=message; $("smsPreviewTo").textContent=number||"(add the extension-worker number)"; $("smsPreview").hidden=false;
  const open=$("smsOpenBtn"); open.hidden=!/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)||!number;
  open.onclick=()=>{ window.location.href=`sms:${number}${/iPhone|iPad/i.test(navigator.userAgent)?"&":"?"}body=${encodeURIComponent(message)}`; };
  $("smsCopyBtn").onclick=async()=>{ try { await navigator.clipboard.writeText(message); toast("SMS text copied."); } catch { toast("Select the text above and copy it."); } };
}
function roundLocation(position) { return {lat:Math.round(position.coords.latitude*100)/100,lon:Math.round(position.coords.longitude*100)/100}; }
function ensureLocation() {
  if(currentLocation) return Promise.resolve(currentLocation);
  if(demoLocationEnabled || !navigator.geolocation) return Promise.resolve(currentLocation={lat:-1.29,lon:36.82});
  return new Promise(resolve=>navigator.geolocation.getCurrentPosition(pos=>{currentLocation=roundLocation(pos);resolve(currentLocation)},()=>{currentLocation={lat:-1.29,lon:36.82};toast("Location unavailable; using demo region.");resolve(currentLocation)},{enableHighAccuracy:false,timeout:6000,maximumAge:600000}));
}
function connectionState() { const online=navigator.onLine; $("connectionDot").classList.toggle("offline",!online); $("connectionLabel").textContent=online?"Connected · auto-sync enabled":"Offline mode · reports stay on device"; $("syncStatus").textContent=online?"Auto-sync is active. Saved reports will send quietly whenever this phone has a connection.":"Offline: reports remain safely on this phone and will send automatically when a connection returns."; if(online)syncQueue({silent:true}); }
function renderQueue() { const queue=getQueue(), list=$("queue"); $("queueCount").textContent=`${queue.length} pending`; $("queueEmpty").hidden=queue.length>0; list.innerHTML=""; queue.slice().reverse().forEach(r=>{const item=document.createElement("div");item.className="queue-item";const context=r.observations?.length?` · ${r.observations.join(", ")}`:"";item.innerHTML=`<b>${displayLabel(r.label)}</b><span>${r.lat.toFixed(2)}, ${r.lon.toFixed(2)}${context} · waiting for network</span>`;list.append(item)}); }

async function loadClassifier() {
  const status=$("modelStatus"), button=$("analyzeBtn");
  try {
    if (!window.tf) throw new Error("TensorFlow.js runtime did not load");
    const [labelMap, model] = await Promise.all([fetch("/model-coffee-v1/class_indices.json").then(r=>r.json()), tf.loadLayersModel("/model-coffee-v1/model.json")]);
    labels=Object.keys(labelMap).sort((a,b)=>Number(a)-Number(b)).map(key=>labelMap[key]); classifier=model;
    // Compiles the WebGL/WASM path now, so the first farmer check is faster.
    const warmup=tf.zeros([1,160,160,3]); const output=classifier.predict(warmup); await output.data(); warmup.dispose(); output.dispose();
    status.textContent=`Coffee model ready · ${labels.length} Arabica leaf conditions · runs on this device`; status.className="model-status ready";
    button.disabled=false; button.textContent="Analyze photo →";
  } catch (error) {
    console.error(error); status.textContent="Model unavailable. Reconnect once to complete the app installation, then it will work offline."; status.className="model-status error"; button.textContent="Model unavailable";
  }
}
async function analyzePhoto() {
  const preview=$("preview");
  if(preview.hidden || !preview.src) return toast("Choose a clear leaf photo first.");
  if(!classifier) return toast("The on-device model is still loading.");
  const button=$("analyzeBtn"); button.disabled=true; button.textContent="Analyzing on this device…";
  try {
    const probabilities=tf.tidy(()=>{
      // MobileNetV2 was trained with RGB pixels normalized to [-1, 1].
      const input=tf.browser.fromPixels(preview).resizeBilinear([160,160]).toFloat().div(127.5).sub(1).expandDims(0);
      return classifier.predict(input);
    });
    const values=await probabilities.data(); probabilities.dispose();
    let best=0; for(let index=1;index<values.length;index++) if(values[index]>values[best])best=index;
    currentResult={label:labels[best],confidence:values[best],uncertain:values[best]<0.60}; savedCurrent=false;
    if(currentResult.uncertain) {
      $("resultLabel").textContent="Uncertain — do not report";
      $("resultText").textContent=`The photo did not confidently match a supported coffee-leaf condition. Closest label: ${displayLabel(currentResult.label)} at ${Math.round(currentResult.confidence*100)}%.`;
      $("advice").innerHTML="<b>Do now:</b> Inspect five leaves on this plant and nearby plants; note whether marks are spreading and check the leaf undersides. Then retake one photo with a single leaf filling most of the frame.<br><b>Do not do yet:</b> Do not spray or save a community report from a low-confidence result. The crop or problem may be outside this MVP's supported classes.";
      $("saveBtn").textContent="Low confidence — not saved"; $("saveBtn").disabled=true;
    } else {
      $("resultLabel").textContent=displayLabel(currentResult.label);
      $("resultText").textContent=`Top model confidence: ${Math.round(currentResult.confidence*100)}%. This is an image-classification result, not confirmation of disease.`;
      renderGuidance(currentResult.label); $("saveBtn").textContent="Save anonymous report"; $("saveBtn").disabled=false;
    }
    $("analysis").classList.add("visible");
  } catch(error) { console.error(error); toast("Could not analyze this image. Try another photo."); }
  finally { button.disabled=false; button.textContent="Analyze photo →"; }
}
async function saveReport() {
  if(!currentResult) return toast("Analyze a leaf before saving a report."); if(currentResult.uncertain)return toast("Low-confidence results are not included in community signals."); if(savedCurrent)return toast("This check is already in your offline queue.");
  const location=await ensureLocation(); const report={id:`field-${crypto.randomUUID?crypto.randomUUID():Date.now()}`,label:currentResult.label,confidence:Number(currentResult.confidence.toFixed(2)),lat:location.lat,lon:location.lon,observations:selectedObservations(),language:$("languageSelect").value,createdAt:new Date().toISOString()};
  const queue=getQueue();queue.push(report);setQueue(queue);renderQueue();savedCurrent=true;$("saveBtn").textContent="Saved to this device ✓";toast("Saved locally. Your photo was not uploaded."); if(navigator.onLine)syncQueue({silent:true});
}
let syncing = false;
async function syncQueue({silent=false}={}) {
  if(!navigator.onLine){if(!silent)toast("Still offline. Your reports remain queued safely.");return}
  if(syncing||!getQueue().length)return; syncing=true;
  $("syncStatus").textContent="Auto-sync: sending queued anonymous signals…";
  try {
    // Remove each report as soon as it is accepted, so a concurrent save is never overwritten.
    for(const report of getQueue()){
      try{const response=await fetch("/api/reports",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(report)});if(!response.ok)throw new Error();setQueue(getQueue().filter(item=>item.id!==report.id));renderQueue()}catch{}
    }
  } finally { syncing=false; }
  const left=getQueue().length; renderQueue();
  $("syncStatus").textContent=left?`Auto-sync paused: ${left} report(s) will retry in a few seconds.`:"Auto-sync complete. Only anonymous signals were shared; photos stay on this phone.";
  if(!silent)toast(left?`${left} report(s) still waiting.`:"Anonymous community signal shared.");
}
function setup() {
  $("photoInput").addEventListener("change",event=>{const file=event.target.files[0];if(!file)return;const preview=$("preview");preview.src=URL.createObjectURL(file);preview.hidden=false;$("cameraCopy").hidden=true;$("analysis").classList.remove("visible");currentResult=null});
  $("sampleBtn").addEventListener("click",async()=>{const preview=$("preview");preview.src="/test-images/coffee-leaf-rust.jpg";preview.hidden=false;$("cameraCopy").hidden=true;$("analysis").classList.remove("visible");await preview.decode();await analyzePhoto();});
  $("analyzeBtn").addEventListener("click",analyzePhoto); $("saveBtn").addEventListener("click",saveReport); $("speakBtn").addEventListener("click",speakAdvice); $("smsBtn").addEventListener("click",composeSms);
  $("languageSelect").addEventListener("change",()=>{ $("voiceNote").textContent=isSwahili()?"Kiswahili pilot: pre-generated offline audio is bundled for coffee-rust and uncertain guidance. Other labels use an installed device voice.":"Voice uses an installed phone voice when available. SMS opens the phone's messaging app; the worker chooses whether to send it."; if(currentResult&&!currentResult.uncertain)renderGuidance(currentResult.label); });
  $("newCheckBtn").addEventListener("click",()=>{$("analysis").classList.remove("visible");$("photoInput").value="";$("preview").hidden=true;$("cameraCopy").hidden=false;$("saveBtn").disabled=false;currentResult=null});
  $("demoLocationBtn").addEventListener("click",()=>{demoLocationEnabled=!demoLocationEnabled;currentLocation=null;$("demoLocationBtn").textContent=demoLocationEnabled?"Demo location enabled ✓":"Use demo location";toast(demoLocationEnabled?"Demo location enabled. Sync remains available.":"Demo location turned off.")});
  window.addEventListener("online",connectionState);window.addEventListener("offline",connectionState);renderQueue();connectionState();setInterval(()=>syncQueue({silent:true}),4000);document.addEventListener("visibilitychange",()=>{if(!document.hidden)syncQueue({silent:true})});if("serviceWorker"in navigator)navigator.serviceWorker.register("/sw.js").catch(()=>{});loadClassifier();
}
setup();
