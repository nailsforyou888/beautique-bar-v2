const clamp=(x)=>Math.max(0,Math.min(1,x));
const range=(p,a,b)=>{const x=clamp((p-a)/(b-a));return x*x*(3-2*x)};
const journey=document.querySelector('.journey');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const $=s=>document.querySelector(s);
const left=$('.left'),right=$('.right'),interior=$('.interior img'),title=$('.c-title'),kicker=$('.c-kicker'),caption=$('.inner-caption'),stone=$('.stone-panel'),hint=$('.hint');
let queued=false;
function draw(){
 queued=false;
 if(reduced.matches)return;
 const p=clamp(-journey.getBoundingClientRect().top/Math.max(1,journey.offsetHeight-innerHeight));
 const split=range(p,.12,.6),calm=range(p,.69,.96);
 left.style.transform=`translateX(${-100*split}%) scale(${1+range(p,0,.15)*.04})`;
 right.style.transform=`translateX(${100*split}%) scale(${1+range(p,0,.15)*.04})`;
 interior.style.transform=`scale(${1.15-.15*split})`;
 title.style.opacity=1-range(p,.02,.25);title.style.transform=`translateY(${-45*range(p,0,.3)}px)`;
 kicker.style.opacity=1-range(p,.02,.18);caption.style.opacity=range(p,.37,.57)*(1-range(p,.69,.8));
 stone.style.clipPath=`inset(${100*(1-calm)}% 0 0)`;hint.style.opacity=1-range(p,0,.12);
}
function schedule(){if(!queued){queued=true;requestAnimationFrame(draw)}}
addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);addEventListener('pageshow',schedule);
new ResizeObserver(schedule).observe(journey);document.fonts.ready.then(schedule);
function setMotion(){
 document.documentElement.classList.toggle('motion-ready',!reduced.matches);
 if(reduced.matches){[left,right,interior,title,kicker,caption,stone,hint].forEach(el=>el.removeAttribute('style'))}
 schedule();
}
const reveals=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible');reveals.unobserve(e.target)}}),{threshold:.12});
document.querySelectorAll('.reveal').forEach(el=>reveals.observe(el));
const rows=[...document.querySelectorAll('.service-row')],images=[...document.querySelectorAll('.service-image img')];
function selectService(index){rows.forEach((r,i)=>r.classList.toggle('active',i===index));images.forEach((im,i)=>im.classList.toggle('active',i===index))}
const servicesObserver=new IntersectionObserver(entries=>{const active=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(active)selectService(rows.indexOf(active.target))},{rootMargin:'-25% 0px -35% 0px',threshold:[0,.5,1]});
rows.forEach((row,i)=>{servicesObserver.observe(row);row.addEventListener('mouseenter',()=>selectService(i));row.addEventListener('focusin',()=>selectService(i))});
const modal=$('dialog');let opener;
document.querySelectorAll('[data-book]').forEach(button=>button.addEventListener('click',()=>{opener=button;modal.showModal()}));
modal.querySelector('button').addEventListener('click',()=>modal.close());
modal.addEventListener('close',()=>opener?.focus());
modal.addEventListener('click',e=>{if(e.target===modal){const r=modal.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)modal.close()}});
reduced.addEventListener('change',setMotion);setMotion();
