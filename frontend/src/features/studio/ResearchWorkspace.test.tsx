import{QueryClient,QueryClientProvider}from"@tanstack/react-query";
import{render,screen}from"@testing-library/react";
import{beforeEach,describe,expect,it,vi}from"vitest";
import ResearchWorkspace from"./ResearchWorkspace";
import{projectApi}from"./projectApi";

vi.mock("./projectApi",()=>({projectApi:{researchStatus:vi.fn(),research:vi.fn(),retryResearch:vi.fn(),approveResearch:vi.fn()}}));
const status={project_id:"p1",project_status:"RESEARCHING",research_status:"RUNNING",progress:35,current_step:"SEARCHING_SOURCES",sources_found:4,facts_verified:0,error_message:null,started_at:null,completed_at:null};
function view(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ResearchWorkspace projectId="p1"/></QueryClientProvider>)}

describe("Research workspace",()=>{
  beforeEach(()=>vi.clearAllMocks());
  it("shows real running progress",async()=>{vi.mocked(projectApi.researchStatus).mockResolvedValue(status);view();expect(await screen.findByText("SEARCHING SOURCES")).toBeInTheDocument();expect(screen.getByText("4 sources found · 0 facts verified")).toBeInTheDocument()});
  it("shows a safe failed state",async()=>{vi.mocked(projectApi.researchStatus).mockResolvedValue({...status,research_status:"FAILED",current_step:"FAILED",error_message:"Provider unavailable"});view();expect(await screen.findByText("Research failed")).toBeInTheDocument();expect(screen.getByText("Provider unavailable")).toBeInTheDocument();expect(screen.getByRole("button",{name:/retry research/i})).toBeInTheDocument()});
  it("renders cited completed evidence and approval",async()=>{vi.mocked(projectApi.researchStatus).mockResolvedValue({...status,project_status:"RESEARCH_COMPLETE",research_status:"COMPLETE",progress:100,current_step:"COMPLETE"});vi.mocked(projectApi.research).mockResolvedValue({project_id:"p1",research_status:"COMPLETE",research_version:"research-v1",generated_at:null,dossier:{executive_summary:"Grounded summary",audience_interest:"Not inferred",why_this_topic_matters:"Review required",key_facts:[{claim:"Museum-supported claim",supporting_source_ids:["src1"],confidence:.8,verification_status:"SUPPORTED",notes:"Verify"}],interesting_facts:[],timeline:[],people:[],locations:[],myths_and_misconceptions:[],controversies_or_uncertainties:[],frequently_asked_questions:[],story_angles:[],visual_opportunities:[],open_questions:[],sources:[{id:"src1",title:"Museum record",url:"https://museum.example/item",publisher:"Museum",domain:"museum.example",excerpt:"Evidence",source_type:"museum_collection",source_quality:"AUTHORITATIVE",authority_reason:"Museum",publication_date:null,retrieved_at:"2026-01-01",relevance:.9}],limitations:["Read full source"]}});view();expect(await screen.findByText("Museum-supported claim")).toBeInTheDocument();expect(screen.getAllByText("Museum record").length).toBeGreaterThan(0);expect(screen.getByRole("button",{name:/approve research/i})).toBeInTheDocument()});
});
