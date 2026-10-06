// This vendor's AbortablePromise.then accepts only onResolve. Await its native
// promise so network/decode rejection reaches our error handling reliably.
export function nativeLoadPromise(request){return request?.promise??request;}
