import{request,send}from"../../api/client";
import type{Project,ResearchDossier,ResearchStart,ResearchStatus}from"../../api/types";

export type ProjectInput={title:string;country:string;language:string;category:string;target_length:string};
export const projectApi={
  create:(body:ProjectInput)=>send<Project>("/api/v1/projects","POST",body),
  get:(id:string,signal?:AbortSignal)=>request<Project>(`/api/v1/projects/${id}`,signal),
  startResearch:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/research/start`,"POST",{}),
  researchStatus:(id:string,signal?:AbortSignal)=>request<ResearchStatus>(`/api/v1/projects/${id}/research/status`,signal),
  research:(id:string,signal?:AbortSignal)=>request<ResearchDossier>(`/api/v1/projects/${id}/research`,signal),
  retryResearch:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/research/retry`,"POST",{}),
  approveResearch:(id:string)=>send<ResearchDossier>(`/api/v1/projects/${id}/research/approve`,"POST",{}),
};
