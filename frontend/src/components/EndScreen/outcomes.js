import { STATUS } from '../../config';

/**
 * Copy and colour for each way a run can end.
 *
 * Three outcomes, not one: the original build only had a victory screen, so
 * losing had no screen at all because losing was not possible.
 */
export const OUTCOMES = {
  [STATUS.ACCESS_GRANTED]: {
    tone: 'granted',
    title: 'ACCESS GRANTED',
    subtitle: 'Marcus unhooks the rope',
    blurb: 'You talked your way past the hardest door in the city. Ask for the corner booth.',
    cta: 'Play again',
  },
  [STATUS.TURNS_EXHAUSTED]: {
    tone: 'refused',
    title: 'THE NIGHT ENDS',
    subtitle: 'Out of turns at the rope',
    blurb: 'The queue moved on without you. You were talking, but you were not landing.',
    cta: 'Try again',
  },
  [STATUS.EJECTED]: {
    tone: 'ejected',
    title: 'MOVE ALONG',
    subtitle: 'Marcus is done with you',
    blurb: 'Money, names and volume have never once worked on this door. Now you know.',
    cta: 'Start over',
  },
};

export const outcomeFor = (status) => OUTCOMES[status] ?? null;
