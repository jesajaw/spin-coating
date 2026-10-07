// Simulated-browser check of index.html (needs: npm install jsdom). Run: node tests/web/dom_check.js
const {JSDOM,VirtualConsole}=require('jsdom'); const fs=require('fs');
const errs=[]; const vc=new VirtualConsole(); vc.on('jsdomError',e=>errs.push(String(e.message||e))); vc.on('error',e=>errs.push(String(e)));
const dom=new JSDOM(fs.readFileSync(require('path').join(__dirname,'..','..','index.html'),'utf8'),{runScripts:'dangerously',virtualConsole:vc,pretendToBeVisual:true,url:'http://localhost/'});
const w=dom.window, d=w.document, $=id=>d.getElementById(id);
const set=(id,v)=>{$(id).value=v;$(id).dispatchEvent(new w.Event('change'));};
const res=[];
function snap(tag){ w.recompute(); const m=$('out-main'); res.push([tag,m.className.includes('error')?'ERROR '+$('out-caption').textContent:m.textContent,$('out-stat1').textContent.slice(0,60)]); }
for (const model of ['emslie','meyerhofer','flack']){
  set('in-model',model);
  for (const law of (model==='flack'?['exponential','flack_table1']:['exponential'])){
    if(model==='flack') set('in-visclaw',law);
    for (const method of ['none','gauss','mc']){
      set('in-method',method);
      // give every sigma a value
      for (const k of ['sigRpm','sigVisc','sigDensity','sigEvap','sigC0','sigH0','sigTime','sigKeta','sigNevap']) w.eval(`F.${k}.set(F.${k}.max*0.02,false)`);
      if (method==='mc') w.eval('F.mcN.set(200,false)');
      snap(`${model}/${law}/${method}`);
      if (model==='flack'&&method==='mc'){ w.runFlackMonteCarlo(); }
    }
    for (const k of ['sigRpm','sigVisc','sigDensity','sigEvap','sigC0','sigH0','sigTime','sigKeta','sigNevap']) w.eval(`F.${k}.set(0,false)`);
  }
}
// preset save + load round trip
set('in-model','flack'); set('in-visclaw','flack_table1'); $('preset-name').value='T1'; $('preset-save').click();
set('in-model','emslie'); set('in-visclaw','exponential'); $('preset-select').value='T1'; $('preset-load').click();
res.push(['preset-roundtrip', $('in-model').value+'/'+$('in-visclaw').value]);
// visibility checks
set('in-model','flack'); set('in-visclaw','flack_table1');
res.push(['paper law: k_eta hidden', $('in-keta').style.display]);
set('in-model','emslie'); res.push(['emslie: evap hidden / h0 shown', $('in-evap').style.display+' / '+($('group-emslie').style.display||'shown')]);
setTimeout(()=>{ res.forEach(r=>console.log(r.join(' | '))); console.log('JS errors:',errs.length); errs.slice(0,5).forEach(e=>console.log('  ',e.slice(0,200))); },300);
