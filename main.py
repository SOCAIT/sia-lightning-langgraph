from src.agentic_systems.bioresearcher_researcher import build_bioresearcher_agent_system

if __name__ == "__main__":
    bioresearcher_agent_system = build_bioresearcher_agent_system()

    config = {"configurable": {"thread_id": "user-123"}}
    result = bioresearcher_agent_system.invoke({"messages": ["Hello, how are you?"], "scientific_context": "..."}, config)
    print(result.get("messages", [])[-1].content)