import{QueryClient}from"@tanstack/react-query";import{ApiError}from"./client";
export const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:30_000,gcTime:300_000,retry:(count,error)=>!(error instanceof ApiError&&error.status<500)&&count<2,refetchOnWindowFocus:false}}});
