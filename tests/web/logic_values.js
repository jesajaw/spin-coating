// Prints reference values of the web logic; tests/test_web_matches_python.py compares them with the Python models.
const L=require('./logic.js');
const base={rpm:3000,rpmRef:3000,viscosityCp:10,densityGcm3:1,evaporationUmS:0.1,solidsFraction:0.1,eScaling:"sqrt",h0Um:100,timeS:30,kEta:18,nEvap:1,viscLaw:"exponential"};
const out={};
for (const [name,ov] of Object.entries({
  emslie:{model:"emslie"}, mey:{model:"meyerhofer"}, mey_const:{model:"meyerhofer",eScaling:"constant"},
  fl_exp:{model:"flack"}, fl_paper:{model:"flack",viscLaw:"flack_table1"}, fl_k0n0:{model:"flack",kEta:0,nEvap:0,eScaling:"constant"}}))
  out[name]=L.thicknessAtRpm({...base,...ov},3000);
const lab={...base,model:"meyerhofer"};
out.mey_rpm6000=L.thicknessAtRpm(lab,6000);
out.fl_rpm6000=L.thicknessAtRpm({...base,model:"flack"},6000);
const sig={rpm:100,viscosityCp:1,densityGcm3:0.02,evaporationUmS:0.01,solidsFraction:0.005,h0Um:0,timeS:0,kEta:0,nEvap:0};
out.gauss_mey=L.sigmaAnalyticNm(lab,sig);
out.gauss_em=L.sigmaAnalyticNm({...base,model:"emslie"},{...sig,h0Um:2,timeS:1});
out.gauss_fl=L.sigmaAnalyticNm({...base,model:"flack"},{...sig,kEta:2,nEvap:0.2});
out.mc_mey=L.propagateMonteCarlo(lab,sig,"gauss",3000,12345).stdNm;
console.log(JSON.stringify(out));
