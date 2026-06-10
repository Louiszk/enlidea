import { Account as ApiUser, ActiveAgent, AgentDirective } from '../api/generated/api';

export interface UserProfile extends ApiUser {
  average_rating: number;
  total_ratings: number;
  average_soundness: number;
  average_significance: number;
  average_novelty: number;
  average_clarity: number;
  total_appreciation_score: number;
  joined_date: string;
  rank?: number;
  score: number;
  follower_count: number;
  total_saves: number;
  total_fulfillments: number;
  total_visits: number;
  total_research_nodes: number;
  active_agents: ActiveAgent[];
}

export interface TerminalOutputItem {
  id: string | number;
  text?: string;
  type?: string;
  isLocal?: boolean;
  isDirectiveRef?: boolean;
  dirId?: number;
  dirSnapshot?: AgentDirective;
}
