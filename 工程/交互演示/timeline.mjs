export function boundedTime(time,duration){return Math.min(duration,Math.max(0,Number.isFinite(time)?time:0));}
export function sourceIndexAt(time,fps,indices,frameTimes=null){
 const values=frameTimes||indices;
 // HTML range serializes doubles; allow sub-nanosecond rounding at a source timestamp.
 const target=frameTimes?Math.max(0,time)+1e-8:Math.max(0,Math.floor(time*fps+1e-8));
 let lo=0,hi=indices.length-1;
 while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(values[mid]<=target)lo=mid;else hi=mid-1;}
 return lo;
}
export function cameraFromPose(p){
 return {position:p.slice(0,3).map(r=>r[3]),forward:p.slice(0,3).map(r=>r[2]),up:p.slice(0,3).map(r=>r[1]===0?0:-r[1])};
}
