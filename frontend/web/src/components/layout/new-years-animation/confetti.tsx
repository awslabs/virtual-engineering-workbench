import JSConfetti from 'js-confetti';

const CONFETTI_RADIUS = 4;
const CONFETTI_NUMBER = 800;

export const createConfetti = () => {
  const jsConfetti = new JSConfetti();
  jsConfetti.addConfetti({
    confettiColors: [
      '#539ce3',
      '#d3e4fb',
      '#8bbbeb',
      '#043463',
      '#456990',
      '#a1bcd4',
      '#94c4f0',
      '#245c9c',
      '#345c84',
      '#24649c'
    ],
    confettiRadius: CONFETTI_RADIUS,
    confettiNumber: CONFETTI_NUMBER
  });
};