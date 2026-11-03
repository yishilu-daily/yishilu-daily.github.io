
(function(){
'use strict';
const $=id=>document.getElementById(id);
const money=n=>'NT$ '+Math.round(n||0).toLocaleString('zh-TW');
const num=id=>Math.max(0,Number($(id).value)||0);
let lastDamageGross=0;

document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
  b.classList.add('active'); $(b.dataset.tab).classList.add('active');
}));

function syncFault(target){
  let v=Math.max(0,Math.min(100,Number($(target).value)||0)); $(target).value=v;
  document.querySelectorAll('.fault-btn[data-target="'+target+'"]').forEach(b=>b.classList.toggle('active',Number(b.dataset.fault)===v));
  if(target==='claimFault') updateClaim();
}
document.querySelectorAll('.fault-btn').forEach(b=>b.addEventListener('click',()=>{$(b.dataset.target).value=b.dataset.fault;syncFault(b.dataset.target);}));
$('damageFault').addEventListener('input',()=>syncFault('damageFault'));
$('claimFault').addEventListener('input',()=>syncFault('claimFault'));

function monthsUsed(a,b){return (b.getFullYear()-a.getFullYear())*12+(b.getMonth()-a.getMonth())+1;}
function depValue(cost,months,rate){
  let v=cost, years=Math.floor(months/12), extra=months%12;
  for(let i=0;i<years;i++) v*=1-rate;
  if(extra>0) v*=1-rate*extra/12;
  return Math.max(v,cost*.1);
}
$('calcDamage').addEventListener('click',()=>{
  $('damageError').hidden=true;
  let vehicle=$('vehicle').value, fr=$('firstDate').value, ar=$('accDate').value;
  if(!vehicle||!fr||!ar){$('damageError').textContent='請完整填寫車種與日期。';$('damageError').hidden=false;return;}
  let f=new Date(fr+'T00:00:00'), a=new Date(ar+'T00:00:00');
  if(a<f){$('damageError').textContent='事故日期不得早於第一次領牌日期。';$('damageError').hidden=false;return;}
  let parts=num('parts'), labor=num('labor'), fault=num('damageFault');
  let months=Math.max(1,monthsUsed(f,a)), rate=vehicle==='car'?.369:.536;
  let after=depValue(parts,months,rate), dep=parts-after, gross=after+labor, claim=gross*fault/100;
  let y=Math.floor(months/12), m=months%12, age=(y?y+' 年 ':'')+(m?m+' 個月':'');
  $('dAge').textContent=age||'1 個月'; $('dRate').textContent=(rate*100).toFixed(1)+'%';
  $('dParts').textContent=money(parts); $('dDep').textContent=money(dep); $('dAfter').textContent=money(after);
  $('dLabor').textContent=money(labor); $('dGross').textContent=money(gross); $('dClaim').textContent=money(claim);
  lastDamageGross=gross; $('sendToClaim').disabled=false;
  localStorage.setItem('yishiluDamage',JSON.stringify({vehicle,fr,ar,parts,labor,fault,gross}));
});
$('sendToClaim').addEventListener('click',()=>{
  $('property').value=Math.round(lastDamageGross); $('claimFault').value=$('damageFault').value; syncFault('claimFault'); updateClaim();
  document.querySelector('.tab[data-tab="claim"]').click();
});
$('clearDamage').addEventListener('click',()=>{
  ['vehicle','firstDate','parts'].forEach(id=>$(id).value=''); $('labor').value=0; $('damageFault').value=100; syncFault('damageFault');
  ['dAge','dRate','dParts','dDep','dAfter','dLabor','dGross','dClaim'].forEach(id=>$(id).textContent='—');
  lastDamageGross=0; $('sendToClaim').disabled=true;
});

const claimFields=[
  ['medical','醫療費用'],
  ['futureMedical','未來必要醫療及復健費'],
  ['lostIncome','工作損失，誤工費'],
  ['care','看護費'],
  ['transport','交通費及其他必要支出'],
  ['property','車輛及其他財產損失'],
  ['solatium','精神慰撫金']
];
function updateClaim(){
  let total=claimFields.reduce((s,[id])=>s+num(id),0), fault=num('claimFault'), paid=num('paid');
  let faulted=total*fault/100, remaining=Math.max(0,faulted-paid);
  $('cTotal').textContent=money(total); $('cFaulted').textContent=money(faulted); $('cPaid').textContent=money(paid); $('cRemaining').textContent=money(remaining);
  $('claimTable').innerHTML='<table class="claim-table"><thead><tr><th>請求項目</th><th>金額</th></tr></thead><tbody>'+
    claimFields.map(([id,name])=>'<tr><td>'+name+'</td><td>'+money(num(id))+'</td></tr>').join('')+
    '</tbody></table>';
  let save={fault,paid}; claimFields.forEach(([id])=>save[id]=num(id)); localStorage.setItem('yishiluClaim',JSON.stringify(save));
}
document.querySelectorAll('.claim-input').forEach(x=>x.addEventListener('input',updateClaim));
$('copyClaim').addEventListener('click',()=>{
  let lines=['藝世錄 車禍民事損害賠償請求清單'];
  claimFields.forEach(([id,name])=>lines.push(name+'：'+money(num(id))));
  lines.push('合計民事損害賠償請求金額：'+$('cTotal').textContent);
  lines.push('依對方肇責比例後參考金額：'+$('cFaulted').textContent);
  lines.push('已領理賠／補償金額：'+$('cPaid').textContent);
  lines.push('目前尚未獲賠參考金額：'+$('cRemaining').textContent);
  if(navigator.clipboard) navigator.clipboard.writeText(lines.join('\n'));
});
$('printClaim').addEventListener('click',()=>window.print());
$('clearClaim').addEventListener('click',()=>{
  claimFields.forEach(([id])=>$(id).value=0); $('paid').value=0; $('claimFault').value=100; syncFault('claimFault'); updateClaim();
});

let t=new Date(), mm=String(t.getMonth()+1).padStart(2,'0'), dd=String(t.getDate()).padStart(2,'0');
$('accDate').value=t.getFullYear()+'-'+mm+'-'+dd;
syncFault('damageFault'); syncFault('claimFault'); updateClaim();
})();
