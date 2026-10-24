setInterval(fetchSFI,3600000);
setInterval(updateGrayline,60000);
fetchSFI();updateGrayline();

function updateDXCC(){
if(!STANDALONE)return;
document.getElementById("k2v-dxcc").innerHTML='<span style="color:#2ecc71">CENTURY: 100/100 ✅</span> <span style="color:#8b949e">→ hunting 101+</span>';
}
updateDXCC();

function updateBars(bc){
if(!STANDALONE)return;
var el=document.getElementById("k2v-bars");
var labels={6:"6",10:"10",12:"12",15:"15",17:"17",20:"20",30:"30",40:"40"};
var max=1;
Object.keys(bc).forEach(function(b){if(bc[b]>max)max=bc[b]});
var html="";
Object.keys(labels).forEach(function(b){
var h=bc[b]?Math.max(4,Math.round(bc[b]/max*28)):2;
var col=bc[b]>=max*0.8?"#50fa7b":bc[b]>=max*0.4?"#f0c040":"#8b949e";
html+='<div style="display:flex;flex-direction:column;align-items:center;gap:1px"><div style="width:14px;height:'+h+'px;background:'+col+';border-radius:2px;transition:height 0.5s"></div><span style="font-size:8px;color:#8b949e;font-family:monospace">'+labels[b]+'</span></div>';
});
el.innerHTML=html;
}

function getBandRec(bc){
var bands=Object.keys(bc);
if(!bands.length)return "";
var counts={};
bands.forEach(function(b){counts[b]=bc[b]});
var sorted=Object.keys(counts).sort(function(a,b){return counts[b]-counts[a]});
var max=counts[sorted[0]]||1;
var labels={6:"6m",10:"10m",12:"12m",15:"15m",17:"17m",20:"20m",30:"30m",40:"40m"};
var str=sorted.slice(0,4).map(function(b){
var lvl=counts[b]>=max*0.8?"HIGH":counts[b]>=max*0.4?"MED":"LOW";
return labels[b]+"("+lvl+")";
}).join(" → ");
return "TUNE: "+str;
}

function pollMain(){
if(paused){mainTimer=setTimeout(pollMain,nextDelay);return}
fetch("https://corsproxy.io")
.then(function(r){
if(r.status===429){nextDelay=300000;document.getElementById("k2v-t").textContent="Rate limited";mainTimer=setTimeout(pollMain,nextDelay);return null}
return r.text()
})
.then(function(d){
if(!d)return;
if(d.trim().length<50){nextDelay=300000;mainTimer=setTimeout(pollMain,nextDelay);return}
nextDelay=300000;
var x=new DOMParser().parseFromString(d,"text/xml");
var sp=x.querySelectorAll("spot");
var tbl=document.getElementById("k2v-tbl");
var rows=tbl.querySelectorAll("tr");
for(var i=rows.length-1;i>4;i--)tbl.deleteRow(i);
var bc={};var hits=[];var newAlert=false;
sp.forEach(function(s){
var b=s.querySelector("band")?s.querySelector("band").textContent:"";
var c=s.querySelector("call")?s.querySelector("call").textContent:"";
var g=s.querySelector("grid")?s.querySelector("grid").textContent:"";
var snr=parseFloat(s.querySelector("snr")?s.querySelector("snr").textContent:"0");
var dx=s.querySelector("dxcc")?parseInt(s.querySelector("dxcc").textContent):0;
if(!BM[b])return;
bc[b]=(bc[b]||0)+1;
var w=W.find(function(w){return w.c===dx});
var reg=w?w.r:"";
var key=c+b+g;
var row=tbl.insertRow();

var c1=row.insertCell(0);c1.style.padding="4px";c1.style.border="1px solid #0066cc";c1.textContent=c;
var c2=row.insertCell(1);c2.style.padding="4px";c2.style.border="1px solid #0066cc";c2.textContent=g;
var c3=row.insertCell(2);c3.style.padding="4px";c3.style.border="1px solid #0066cc";c3.textContent=b;
var c4=row.insertCell(3);c4.style.padding="4px";c4.style.border="1px solid #0066cc";c4.style.color=snr<=-15?"#f0c040":"#c9d1d9";c4.textContent=snr.toFixed(1);
var c5=row.insertCell(4);c5.style.padding="4px";c5.style.border="1px solid #0066cc";c5.textContent=dx;
var c6=row.insertCell(5);c6.style.padding="4px";c6.style.border="1px solid #0066cc";c6.style.color=RC[reg]||"#8b949e";c6.textContent=reg;

if(reg&&snr<=-15){
hits.push(c+" "+b+" "+snr+"dB "+(w?w.n:""));
if(!seenMain[key]){
newAlert=true;seenMain[key]=1;
var msg=c+" "+b+" "+snr+"dB "+(w?w.n:"");
lastAlertMsg=new Date().toLocaleTimeString()+" — "+msg;
if(STANDALONE){
document.getElementById("k2v-last").textContent="⚡ Last: "+lastAlertMsg;
sessionQSOs.unshift(c+" "+b+" "+snr+"dB");
if(sessionQSOs.length>5)sessionQSOs.pop();
document.getElementById("k2v-last5").textContent="RECENT: "+sessionQSOs.join(" | ");
lastQSOtime=Date.now();
}
fireNotification(msg);
}
}
});
var rec=getBandRec(bc);
document.getElementById("k2v-b").textContent=rec||"Bands: none active";
var wEl=document.getElementById("k2v-w");
wEl.textContent="";
if(!sp.length){
wEl.style.textAlign="center";wEl.style.padding="20px 0";wEl.style.color="#8b949e";wEl.textContent="📡 Waiting for FT8 spots…";
}else{
if(hits.length){
wEl.style.textAlign="left";wEl.style.padding="0";wEl.style.color="#f0c040";
var bld=document.createElement("b");bld.textContent="⚡ ≤-15dB targets: ";wEl.appendChild(bld);
var txt=document.createTextNode(hits.slice(0,5).join(" | "));wEl.appendChild(txt);
}else{
wEl.style.textAlign="left";wEl.style.padding="0";wEl.style.color="#8b949e";wEl.textContent="No ≤-15dB AS/AF/OC targets in last 15 min";
}
}
document.getElementById("k2v-t").textContent=new Date().toLocaleTimeString()+" · "+sp.length+" spots";
if(STANDALONE)updateBars(bc);
if(newAlert&&audioCtx)playAlert();
mainTimer=setTimeout(pollMain,nextDelay);
})
.catch(function(e){document.getElementById("k2v-t").textContent="ERR: "+e.message;document.getElementById("k2v-b").textContent="RETRY IN 5 MIN";nextDelay=300000;mainTimer=setTimeout(pollMain,nextDelay)});
}

function pollDX(){
if(paused){dxTimer=setTimeout(pollDX,dxDelay);return}
var el=document.getElementById("k2v-dxlist");
var results=[];
var done=0;
DXW.forEach(function(dx){
fetch("https://corsproxy.io"+dx.call+"&flowStartSeconds=-900&mode=FT8")
.then(function(r){return r.text()})
.then(function(d){
var x=new DOMParser().parseFromString(d,"text/xml");
var sp=x.querySelectorAll("spot");
sp.forEach(function(s){
var rc=s.querySelector("rc")?s.querySelector("rc").textContent:"";
var rg=s.querySelector("rg")?s.querySelector("rg").textContent:"";
var b=s.querySelector("band")?s.querySelector("band").textContent:"";
var snr=parseFloat(s.querySelector("snr")?s.querySelector("snr").textContent:"0");
var f=s.querySelector("f")?s.querySelector("f").textContent:"";
if(rg&&rg.indexOf("FM")===0&&BM[b]){
results.push({call:dx.call,name:dx.name,rc:rc,rg:rg,band:b,snr:snr,freq:(f/1000000).toFixed(3)});
}
});
done++;
if(done===DXW.length){renderDX();dxTimer=setTimeout(pollDX,dxDelay)}
})
.catch(function(){done++;if(done===DXW.length){renderDX();dxTimer=setTimeout(pollDX,dxDelay)}});
});

function renderDX(){
el.textContent="";
if(!results.length){
el.style.color="#8b949e";el.textContent="No DX watch targets heard near FM18 in last 15 min";return;
}
results.sort(function(a,b){return b.snr-a.snr});
var newAlert=false;
results.slice(0,8).forEach(function(r){
var key=r.call+r.rc+r.band;
if(!seenDX[key]){
newAlert=true;seenDX[key]=1;
var msg=r.call+" ("+r.name+") "+r.band+" "+r.freq+"MHz via "+r.rc;
lastAlertMsg=new Date().toLocaleTimeString()+" — "+msg;
if(STANDALONE)document.getElementById("k2v-last").textContent="⚡ Last: "+lastAlertMsg;
fireNotification(msg);
}
var div=document.createElement("div");div.style.margin="2px 0";
var bCall=document.createElement("b");bCall.style.color="#f0c040";bCall.textContent=r.call;div.appendChild(bCall);
var sName=document.createElement("span");sName.style.color="#c9d1d9";sName.textContent=" ("+r.name+") — heard by ";div.appendChild(sName);
var bRc=document.createElement("b");bRc.textContent=r.rc;div.appendChild(bRc);
var sRg=document.createElement("span");sRg.style.color="#8b949e";sRg.textContent=" ("+r.rg+") on ";div.appendChild(sRg);
var bBand=document.createElement("b");bBand.style.color="#50fa7b";bBand.textContent=r.band+" "+r.freq+" MHz ";div.appendChild(bBand);
var sAt=document.createTextNode("@ ");div.appendChild(sAt);
var sSnr=document.createElement("span");sSnr.style.color=r.snr<=-15?"#f0c040":"#c9d1d9";sSnr.textContent=r.snr.toFixed(1)+" dB";div.appendChild(sSnr);
el.appendChild(div);
});
if(newAlert&&audioCtx)playAlert();
}
}

document.getElementById("k2v-btn-test").addEventListener("click",function(){initAudio();playAlert()});
document.getElementById("k2v-btn-pull").addEventListener("click",pullNow);
document.getElementById("k2v-pause").addEventListener("click",togglePause);
document.getElementById("k2v-fs").addEventListener("click",toggleFS);
document.addEventListener("click",initAudio,{once:true});
document.addEventListener("keydown",initAudio,{once:true});

window.initAudio=initAudio;
window.playAlert=playAlert;
window.togglePause=togglePause;
window.toggleFS=toggleFS;
window.pullNow=pullNow;
pollMain();
pollDX();
})();
</script>
</body></html>

