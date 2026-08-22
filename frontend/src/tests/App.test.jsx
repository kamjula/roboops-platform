import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import App from "../App.jsx";

describe("App", () => {
  it("renders the public login page without the application shell", async () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText("RoboOps")).not.toBeInTheDocument();
  });
});
