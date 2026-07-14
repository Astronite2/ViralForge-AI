import{lazy,Suspense}from"react";
import{Navigate,Route,Routes}from"react-router-dom";
import{PageLoading}from"./components/ui";
import{AppShell}from"./layout/AppShell";

const Studio=lazy(()=>import("./features/studio/StudioHomePage"));
const Project=lazy(()=>import("./features/studio/ProjectPage"));
const Dashboard=lazy(()=>import("./features/dashboard/DashboardPage"));
const Topics=lazy(()=>import("./features/topics/TopicsPage"));
const TopicDetails=lazy(()=>import("./features/topics/TopicDetailsPage"));
const Decisions=lazy(()=>import("./features/decisions/DecisionsPage"));
const DecisionDetails=lazy(()=>import("./features/decisions/DecisionDetailsPage"));
const Evidence=lazy(()=>import("./features/evidence/EvidencePage"));
const Reasoning=lazy(()=>import("./features/reasoning/ReasoningPage"));
const History=lazy(()=>import("./features/history/HistoryPage"));
const Graph=lazy(()=>import("./features/graph/KnowledgeGraphPage"));
const SettingsPage=lazy(()=>import("./features/settings/SettingsPage"));
const Money=lazy(()=>import("./features/money/MoneyOpportunitiesPage"));

export default function App(){return <Suspense fallback={<PageLoading/>}><Routes><Route index element={<Studio/>}/><Route path="projects/:id" element={<Project/>}/><Route element={<AppShell/>}><Route path="money-opportunities" element={<Money/>}/><Route path="dashboard" element={<Dashboard/>}/><Route path="topics" element={<Topics/>}/><Route path="topics/:topicId" element={<TopicDetails/>}/><Route path="decisions" element={<Decisions/>}/><Route path="decisions/:decisionId" element={<DecisionDetails/>}/><Route path="evidence" element={<Evidence/>}/><Route path="reasoning" element={<Reasoning/>}/><Route path="history" element={<History/>}/><Route path="knowledge-graph" element={<Graph/>}/><Route path="settings" element={<SettingsPage/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes></Suspense>}
