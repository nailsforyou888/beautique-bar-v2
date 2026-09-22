const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ease=x=>{x=clamp(x);return x*x*(3-2*x)};
const range=(p,a,b)=>ease((p-a)/(b-a));
const root=document.documentElement,journey=document.querySelector('.journey');
const media=matchMedia('(prefers-reduced-motion: reduce)');
let queued=false;
function draw(){queued=false;const travel=journey.offsetHeight-innerHeight;const p=media.matches?0:clamp(-journey.getBoundingClientRect().top/Math.max(1,travel));root.style.setProperty('--progress',p);window.renderScene(p,media.matches)}
function schedule(){if(!queued){queued=true;requestAnimationFrame(draw)}}
addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);addEventListener('pageshow',schedule);media.addEventListener('change',schedule);new ResizeObserver(schedule).observe(journey);document.fonts.ready.then(schedule);
const modal=document.querySelector('dialog');document.querySelectorAll('[data-book]').forEach(b=>b.addEventListener('click',()=>modal.showModal()));modal.querySelector('button').addEventListener('click',()=>modal.close());modal.addEventListener('click',e=>{if(e.target===modal){const r=modal.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)modal.close()}});schedule();
