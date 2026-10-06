export function controlAvailability({loading,ready,saved,mode}){
 return {mode:!loading,scene:!loading&&mode!=='points',map:!loading&&ready,restore:!loading&&ready&&saved};
}
