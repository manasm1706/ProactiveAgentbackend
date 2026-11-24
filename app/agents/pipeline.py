from datetime import datetime
from app.agents.base import CustomerContext
from app.agents.implementations import SignalIngestionAgent, BehaviorShiftAgent, NeedInferenceAgent, NextBestActionAgent, MessageGenerationAgent, ChannelTimingAgent, SuppressionAgent, ResponseTrackingAgent, EscalationAgent

class OrchestratorAgent:
    def __init__(self, ai_service):
        self.ai_service=ai_service
        self.agents=[SignalIngestionAgent(),BehaviorShiftAgent(),NeedInferenceAgent(ai_service),NextBestActionAgent(),MessageGenerationAgent(ai_service),ChannelTimingAgent(),SuppressionAgent(),ResponseTrackingAgent(),EscalationAgent()]
    def run(self, context):
        stages=[]
        for agent in self.agents:
            result=agent.run(context)
            stages.append({"agent":agent.name, **result})
        esc=context.escalation.get("required",False)
        suppressed=context.suppression.get("suppressed",False)
        if esc:
            status="ESCALATED TO HUMAN"
        elif suppressed:
            status="DO NOT CONTACT" if context.suppression.get("reason") in ["CONSENT BLOCK","OPT-OUT"] else "SUPPRESSED"
        else:
            status="READY FOR CUSTOMER ENGAGEMENT"
        context.final_decision={"customer_id":context.customer.get("customer_id"),"observed":context.behavior_analysis.get("observed"),"possible_interpretation":context.need_inference.get("possible_need"),"confidence":context.need_inference.get("confidence",0.0),"priority":context.next_best_action.get("priority"),"recommended_action":context.next_best_action.get("action"),"channel":context.channel.get("channel"),"message":context.message.get("message"),"suppression":context.suppression,"escalation":context.escalation,"final_status":status}
        return {"stages":stages,"decision":context.final_decision,"context":context}
