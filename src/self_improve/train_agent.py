import agentlightning as agl

from src
# Run 4 agents in parallel
strategy = {
    "type": "cs",  # Client-Server
    "n_runners": 4,
    "server_port": 48000
}
# LLM Proxy for model routing
proxy_config = {
    "port": 48001,
    "model_list": [
        {"model_name": "Qwen/Qwen2-1.5B-Instruct", 
         "litellm_params": {"model": "ollama/qwen2:1.5b"}},
        {"model_name": "senior_researcher_llm",  # Training target
         "litellm_params": {"model": "ollama/llama3"}},
        {"model_name": "mistralai/Mixtral-8x7B-Instruct-v0.1",
         "litellm_params": {"model": "ollama/mixtral"}}
    ]
}
# Real-time monitoring
monitoring_hook = WandbLoggingHook(project_name="AI-Research-Lab")


def full_training_pipeline():
    
    # === Phase 1: Initial Data Collection ===
    print("📊 Phase 1: Gathering baseline data...")
    
    trainer = agl.Trainer(
        n_runners=4,
        strategy=strategy,
        hooks=[monitoring_hook]
    )
    
    agent = MedicalResearchAgent(graph, protocol_evaluator)
    trainer.dev(agent, train_data[:10])  # Quick 10-sample run
    
    # === Phase 2: Train Junior Researchers (SFT) ===
    print("🎓 Phase 2: Training juniors with SFT...")
    
    sft_trainer = agl.Trainer(algorithm=SFTOnSuccess())
    sft_trainer.fit(agent)  # Learns from successful traces
    
    # === Phase 3: Train Senior Researchers (PPO) ===
    print("🎮 Phase 3: Training seniors with PPO...")
    
    ppo_config = {
        "algorithm": {"adv_estimator": "grpo"},
        "data": {"train_batch_size": 4},
        "actor_rollout_ref": {
            "model": {"path": "meta-llama/Llama-3-8B-Instruct"}
        },
        "trainer": {
            "total_training_steps": 100,
            "test_freq": 10
        }
    }
    
    ppo_trainer = agl.Trainer(
        algorithm=agl.VERL(ppo_config),
        n_runners=4,
        strategy=strategy,
        adapter=custom_adapter,
        hooks=[monitoring_hook]
    )
    
    ppo_trainer.fit(agent, train_data, val_data)
    
    # === Phase 4: Train Supervisor (Contextual Bandit) ===
    print("🎰 Phase 4: Training supervisor with bandit...")
    
    bandit_trainer = agl.Trainer(algorithm=ContextualBandit())
    bandit_trainer.fit(agent)
    
    print("✅ Training complete!")
# Execute
full_training_pipeline()