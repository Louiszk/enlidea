export const allTags = ["All Tags", "General", "Theoretical", "Technological", "Strategic", "Social", "Scientific", "Psychological", "Predictive", "Political", "Philosophical", "Management", "Legal", "Innovation", "Historical", "Health", "Ethical", "Environmental", "Engineering", "Educational", "Economic", "Design", "Cultural", "Business", "Artistic"];
export const allTypes = ["All Types", "Research Node", "Hypothesis", "Algorithm", "Dataset"];

export const plural = (word) => {
    if (word.toLowerCase() === 'theory') {
      return 'Theories';
    }
    if (word.toLowerCase() === 'hypothesis') {
      return 'Hypotheses';
    }
    return word + 's';
  };