import random
import math

# Simulation Constants
NUM_AGENTS = 100
INITIAL_BLUE_STARS = 500.0
INITIAL_ORANGE_STARS = 10.0
NUM_CYCLES = 10000
DEPLOYMENT_FEE = 50.0
CREATION_FEE = 5.0
MIN_STAKE = 2.0
REVIEWER_BS_REWARD = 2.0
TAX_RATE = 0.02
MIN_OS_PENALTY = 5.0
BAN_THRESHOLD_OS = -20.0


class Agent:
    def __init__(self, id, persona):
        self.id = id
        self.persona = persona
        self.blue_stars = INITIAL_BLUE_STARS - DEPLOYMENT_FEE
        self.orange_stars = INITIAL_ORANGE_STARS
        self.is_active = True

    def is_eligible_worker(self, bounty, min_trust_required):
        if not self.is_active:
            return False

        stake = max(MIN_STAKE, bounty * 0.10)
        if self.blue_stars < stake:
            return False

        # Trust logic: 0-bounty nodes have NO requirement. Paid nodes require 0.0+ OS or node specific min.
        if bounty > 0:
            actual_min = max(0.0, min_trust_required)
            if self.orange_stars < actual_min:
                return False

        if self.persona == "Ambitious" and bounty < 500:
            return False
        return True

    def is_eligible_reviewer(self, bounty, min_trust_required):
        if not self.is_active:
            return False

        # Reviewers must meet the same trust floor as workers for paid bounties
        if bounty > 0:
            actual_min = max(0.0, min_trust_required)
            if self.orange_stars < actual_min:
                return False

        return True

    def attempt_task(self):
        probs = {"Honest": 0.85, "Ambitious": 0.60, "Spammer": 0.15}
        return random.random() < probs[self.persona]

    def vote(self, actual_success):
        if self.persona == "Honest":
            return (
                ("ACCEPT" if actual_success else "REJECT")
                if random.random() < 0.90
                else ("REJECT" if actual_success else "ACCEPT")
            )
        if self.persona == "Ambitious":
            return (
                ("ACCEPT" if actual_success else "REJECT")
                if random.random() < 0.75
                else ("REJECT" if actual_success else "ACCEPT")
            )
        if self.persona == "Spammer":
            return "ACCEPT"
        return "REJECT"

    def apply_penalty(self):
        penalty = max(MIN_OS_PENALTY, self.orange_stars * 0.10)
        self.orange_stars -= penalty
        if self.orange_stars < BAN_THRESHOLD_OS:
            self.is_active = False


def run_simulation():
    agents = []
    # 60% Honest, 20% Ambitious, 20% Spammer
    for i in range(NUM_AGENTS):
        if i < 60:
            persona = "Honest"
        elif i < 80:
            persona = "Ambitious"
        else:
            persona = "Spammer"
        agents.append(Agent(i, persona))

    treasury_balance = 10000.0
    total_tax_to_treasury = 0

    for _ in range(NUM_CYCLES):
        # Occasionally simulate 0-bounty node for grinding OS
        if random.random() < 0.15:
            bounty = 0
            min_trust_required = 0.0
        else:
            # Tailed exponential: mean of 200, but occasionally very high
            bounty = int(random.expovariate(1 / 200))
            bounty = max(50, bounty)  # Minimum 50 for paid nodes

            # Realistic min_trust setting: some high-bounty nodes require high trust
            if bounty > 300 and random.random() < 0.5:
                min_trust_required = random.uniform(10.0, 50.0)
            else:
                min_trust_required = 0.0

        # 1. Selection: Coordinator
        potential_coordinators = [a for a in agents if a.blue_stars >= (bounty + CREATION_FEE) and a.is_active]
        if not potential_coordinators:
            continue
        coordinator = random.choice(potential_coordinators)

        # 2. Selection: Workers
        eligible_workers = [a for a in agents if a.is_eligible_worker(bounty, min_trust_required)]
        if not eligible_workers:
            continue

        group_size = random.randint(1, 3)
        fulfilling_agents = random.sample(eligible_workers, min(len(eligible_workers), group_size))

        # 3. Selection: Reviewers
        potential_reviewers = [
            a
            for a in agents
            if a.id != coordinator.id
            and a not in fulfilling_agents
            and a.is_eligible_reviewer(bounty, min_trust_required)
        ]
        if len(potential_reviewers) < 3:
            continue
        reviewers = random.sample(potential_reviewers, 3)

        # --- EXECUTION ---
        # Coordinator pays bounty + network fee
        coordinator.blue_stars -= bounty + CREATION_FEE
        treasury_balance += CREATION_FEE

        stake_per_worker = max(MIN_STAKE, bounty * 0.10)
        for a in fulfilling_agents:
            a.blue_stars -= stake_per_worker

        actual_success = all(a.attempt_task() for a in fulfilling_agents)
        votes = [r.vote(actual_success) for r in reviewers]
        consensus = "ACCEPT" if votes.count("ACCEPT") >= 2 else "REJECT"

        worker_os_raw = math.log(max(bounty, 1), 1.5)
        worker_os_reward = max(1.0, worker_os_raw)
        reviewer_os_reward = worker_os_reward * 0.25
        accuracy_bonus_bs = reviewer_os_reward * 2.0

        if consensus == "ACCEPT":
            # PUBLISHED (Consensus)
            tax = bounty * TAX_RATE
            treasury_balance += tax
            total_tax_to_treasury += tax

            net_bounty = bounty - tax
            stake_return = stake_per_worker

            # 80/20 Payout Split
            base_pool = net_bounty * 0.80
            merit_pool = net_bounty * 0.20
            total_os = sum(max(0, a.orange_stars) for a in fulfilling_agents)

            for a in fulfilling_agents:
                share = base_pool / len(fulfilling_agents)
                if total_os > 0:
                    share += merit_pool * (max(0, a.orange_stars) / total_os)
                else:
                    share += merit_pool / len(fulfilling_agents)

                a.blue_stars += share + stake_return
                a.orange_stars += worker_os_reward

            # Reviewers
            for i, r in enumerate(reviewers):
                # A. Base Reward
                if treasury_balance >= REVIEWER_BS_REWARD:
                    treasury_balance -= REVIEWER_BS_REWARD
                    r.blue_stars += REVIEWER_BS_REWARD

                # B. Accuracy Bonus
                if votes[i] == "ACCEPT":
                    if treasury_balance >= accuracy_bonus_bs:
                        treasury_balance -= accuracy_bonus_bs
                        r.blue_stars += accuracy_bonus_bs
                    r.orange_stars += reviewer_os_reward
                else:
                    r.apply_penalty()
        else:
            # REJECTED (Consensus)
            coordinator.blue_stars += bounty

            # Workers lose stake to Treasury and suffer flat penalty
            treasury_balance += stake_per_worker * len(fulfilling_agents)
            for a in fulfilling_agents:
                a.apply_penalty()

            # Reviewers
            for i, r in enumerate(reviewers):
                # A. Base Reward
                if treasury_balance >= REVIEWER_BS_REWARD:
                    treasury_balance -= REVIEWER_BS_REWARD
                    r.blue_stars += REVIEWER_BS_REWARD

                # B. Accuracy Bonus
                if votes[i] == "REJECT":
                    if treasury_balance >= accuracy_bonus_bs:
                        treasury_balance -= accuracy_bonus_bs
                        r.blue_stars += accuracy_bonus_bs
                    r.orange_stars += reviewer_os_reward
                else:
                    r.apply_penalty()

    # Output Report
    total_blue = sum(a.blue_stars for a in agents)
    total_orange = sum(a.orange_stars for a in agents)
    banned_count = sum(1 for a in agents if not a.is_active)

    print("\n" + "=" * 50)
    print("       ENLIDEA TOKENOMIC SIMULATION REPORT (V7)")
    print("=" * 50)
    print(f"Treasury Balance:   {treasury_balance:,.2f}")
    print(f"Total Blue Stars:   {total_blue:,.2f}")
    print(f"Total Orange Stars: {total_orange:,.2f}")
    print(f"Banned Agents:      {banned_count}")
    print("-" * 50)
    print(f"{'Persona':<12} | {'Avg Blue':<15} | {'Avg Orange':<15}")
    print("-" * 50)

    for p in ["Honest", "Ambitious", "Spammer"]:
        p_agents = [a for a in agents if a.persona == p]
        avg_blue = sum(a.blue_stars for a in p_agents) / len(p_agents)
        avg_orange = sum(a.orange_stars for a in p_agents) / len(p_agents)
        print(f"{p:<12} | {avg_blue:<15,.2f} | {avg_orange:<15,.2f}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    run_simulation()
