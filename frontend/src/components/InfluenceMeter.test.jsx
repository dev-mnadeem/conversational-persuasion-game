import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InfluenceMeter } from './InfluenceMeter';
import { STATUS } from '../config';

const renderMeter = (props = {}) =>
  render(
    <InfluenceMeter
      score={40}
      threshold={100}
      turnsRemaining={8}
      maxTurns={12}
      status={STATUS.IN_PROGRESS}
      {...props}
    />,
  );

describe('InfluenceMeter', () => {
  it('shows the running score against the threshold', () => {
    renderMeter();
    expect(screen.getByText('40 / 100')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '40');
  });

  it('fills proportionally', () => {
    const { container } = renderMeter({ score: 25 });
    expect(container.querySelector('.meter-fill')).toHaveStyle({ width: '25%' });
  });

  it('never overfills past the threshold', () => {
    const { container } = renderMeter({ score: 140 });
    expect(container.querySelector('.meter-fill')).toHaveStyle({ width: '100%' });
  });

  it('marks the bar as dangerous below zero', () => {
    const { container } = renderMeter({ score: -20 });
    expect(container.querySelector('.meter-danger')).toBeInTheDocument();
    expect(container.querySelector('.meter-fill')).toHaveStyle({ width: '0%' });
  });

  it('switches tone when the door opens', () => {
    const { container } = renderMeter({ score: 104, status: STATUS.ACCESS_GRANTED });
    expect(container.querySelector('.meter-fill.granted')).toBeInTheDocument();
  });

  it('counts the turns left', () => {
    renderMeter({ turnsRemaining: 8 });
    expect(screen.getByText('8 TURNS LEFT')).toBeInTheDocument();
  });

  it('uses the singular on the final turn and warns about it', () => {
    const { container } = renderMeter({ turnsRemaining: 1 });
    expect(screen.getByText('1 TURN LEFT')).toBeInTheDocument();
    expect(container.querySelector('.meter-turns.urgent')).toBeInTheDocument();
  });
});
