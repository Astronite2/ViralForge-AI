import{QueryClient,QueryClientProvider}from"@tanstack/react-query";
import{render,screen}from"@testing-library/react";
import{MemoryRouter}from"react-router-dom";
import{describe,expect,it}from"vitest";
import StudioHomePage from"./StudioHomePage";

describe("ViralForge Studio",()=>{
  it("starts with a production project form and honest defaults",()=>{
    const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
    render(<QueryClientProvider client={client}><MemoryRouter><StudioHomePage/></MemoryRouter></QueryClientProvider>);
    expect(screen.getByRole("heading",{name:"What video should we create today?"})).toBeInTheDocument();
    expect(screen.getByLabelText("Topic")).toBeInTheDocument();
    expect(screen.getByDisplayValue("United States")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Documentary")).toBeInTheDocument();
    expect(screen.getByRole("button",{name:/start project/i})).toBeDisabled();
  });
});
