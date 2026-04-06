import { useState, useEffect, useCallback } from 'react';

// Module-level state to share across components without a Provider or Zustand
let state = {
  isActive: false,
  steps: [],
  currentStepIndex: 0,
  targetChartIndex: null,
};

let listeners = new Set();

const notify = () => {
  listeners.forEach(listener => listener(state));
};

export const useAgent = () => {
  const [localState, setLocalState] = useState(state);

  useEffect(() => {
    listeners.add(setLocalState);
    return () => {
      listeners.delete(setLocalState);
    };
  }, []);

  const activateNarrator = useCallback((steps, targetChartIndex) => {
    state = {
      ...state,
      isActive: true,
      steps: steps || [],
      currentStepIndex: 0,
      targetChartIndex: targetChartIndex,
    };
    notify();
  }, []);

  const nextStep = useCallback(() => {
    state = {
      ...state,
      currentStepIndex: state.currentStepIndex + 1,
    };
    notify();
  }, []);

  const prevStep = useCallback(() => {
    state = {
      ...state,
      currentStepIndex: Math.max(0, state.currentStepIndex - 1),
    };
    notify();
  }, []);

  const exitNarrator = useCallback(() => {
    state = {
      isActive: false,
      steps: [],
      currentStepIndex: 0,
      targetChartIndex: null,
    };
    notify();
  }, []);

  return {
    ...localState,
    activateNarrator,
    nextStep,
    prevStep,
    exitNarrator,
  };
};
