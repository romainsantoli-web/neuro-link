import '@testing-library/jest-dom';

// jsdom doesn't implement scrollIntoView — stub it
Element.prototype.scrollIntoView = () => {};
