import{request,send}from"../../api/client";
import type{ProducerBrief,ProducerStatus,Project,ProjectScript,ResearchDossier,ResearchGaps,ResearchStart,ResearchStatus,ScriptStatus}from"../../api/types";

export type ProjectInput={title:string;country:string;language:string;category:string;target_length:string};
export const projectApi={
  create:(body:ProjectInput)=>send<Project>("/api/v1/projects","POST",body),
  get:(id:string,signal?:AbortSignal)=>request<Project>(`/api/v1/projects/${id}`,signal),
  startResearch:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/research/start`,"POST",{}),
  researchStatus:(id:string,signal?:AbortSignal)=>request<ResearchStatus>(`/api/v1/projects/${id}/research/status`,signal),
  research:(id:string,signal?:AbortSignal)=>request<ResearchDossier>(`/api/v1/projects/${id}/research`,signal),
  retryResearch:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/research/retry`,"POST",{}),
  approveResearch:(id:string)=>send<ResearchDossier>(`/api/v1/projects/${id}/research/approve`,"POST",{}),
  researchGaps:(id:string,signal?:AbortSignal)=>request<ResearchGaps>(`/api/v1/projects/${id}/research/gaps`,signal),
  expandResearch:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/research/expand`,"POST",{target_duration_minutes:15,focus_areas:[],max_additional_sources:25}),
  startBrief:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/production-brief/start`,"POST",{}),
  briefStatus:(id:string,signal?:AbortSignal)=>request<ProducerStatus>(`/api/v1/projects/${id}/production-brief/status`,signal),
  brief:(id:string,signal?:AbortSignal)=>request<ProducerBrief>(`/api/v1/projects/${id}/production-brief`,signal),
  approveBrief:(id:string)=>send<ProducerBrief>(`/api/v1/projects/${id}/production-brief/approve`,"POST",{}),
  retryBrief:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/production-brief/retry`,"POST",{}),
  rejectBrief:(id:string)=>send<ProducerBrief>(`/api/v1/projects/${id}/production-brief/reject`,"POST",{}),
  regenerateBrief:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/production-brief/regenerate`,"POST",{}),
  startScript:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/script/start`,"POST",{}),
  scriptStatus:(id:string,signal?:AbortSignal)=>request<ScriptStatus>(`/api/v1/projects/${id}/script/status`,signal),
  script:(id:string,signal?:AbortSignal)=>request<ProjectScript>(`/api/v1/projects/${id}/script`,signal),
  approveScript:(id:string)=>send<ProjectScript>(`/api/v1/projects/${id}/script/approve`,"POST",{}),
  retryScript:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/script/retry`,"POST",{}),
  regenerateScript:(id:string)=>send<ResearchStart>(`/api/v1/projects/${id}/script/regenerate`,"POST",{}),
  rejectScript:(id:string)=>send<ProjectScript>(`/api/v1/projects/${id}/script/reject`,"POST",{}),
};
