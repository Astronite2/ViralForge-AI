import{request,send}from"../../api/client";
import type{Project}from"../../api/types";

export type ProjectInput={title:string;country:string;language:string;category:string;target_length:string};
export const projectApi={
  create:(body:ProjectInput)=>send<Project>("/api/v1/projects","POST",body),
  get:(id:string,signal?:AbortSignal)=>request<Project>(`/api/v1/projects/${id}`,signal),
  startResearch:(id:string)=>send<Project>(`/api/v1/projects/${id}/research/start`,"POST",{}),
};
