const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const unit=a=>{const n=Math.hypot(...a);return a.map(v=>v/n);};
function rotate(v,axis,angle){const c=Math.cos(angle),s=Math.sin(angle),k=dot(axis,v)*(1-c),p=cross(axis,v);return v.map((x,i)=>x*c+p[i]*s+axis[i]*k);}
export function lookDirection(direction,up,dx,dy){
 const u=unit(up),f=unit(direction),yaw=rotate(f,u,-dx*.002);
 const pitch=Math.asin(Math.max(-1,Math.min(1,dot(yaw,u))));
 const next=Math.max(-Math.PI/2+.02,Math.min(Math.PI/2-.02,pitch-dy*.002));
 return unit(rotate(yaw,unit(cross(yaw,u)),next-pitch));
}
