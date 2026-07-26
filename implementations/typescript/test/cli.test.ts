import {describe, expect, it} from 'vitest';

import {createProgram} from '../src/cli.js';

describe('createProgram', () => {
  it('uses the shared version text', () => {
    expect(createProgram().version()).toBe(
      'polytui 0.1.0-dev.0 (typescript)',
    );
  });
});
