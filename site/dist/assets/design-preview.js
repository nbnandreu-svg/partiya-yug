/* Local-only controls. Never shown on the published site. */
(() => {
  if (!['localhost', '127.0.0.1', '[::1]'].includes(location.hostname) || new URLSearchParams(location.search).get('design') !== '1') return;
  const panel = document.createElement('details');
  panel.className = 'design-panel';
  const summary = document.createElement('summary');
  summary.textContent = 'Настройка предпросмотра';
  panel.append(summary);
  const settings = [
    ['Отступы', '--density', 0.8, 1.3, 0.05, 1, ''],
    ['Заголовки', '--type-scale', 0.9, 1.05, 0.025, 1, ''],
    ['Скругление', '--radius', 0, 18, 1, 5, 'px'],
    ['Движение', '--motion', 0, 2, 0.25, 1, '']
  ];
  const inputs = [];
  for (const [name, property, min, max, step, value, unit] of settings) {
    const label = document.createElement('label');
    label.textContent = name;
    const input = document.createElement('input');
    Object.assign(input, { type: 'range', min, max, step, value });
    input.addEventListener('input', () => document.documentElement.style.setProperty(property, input.value + unit));
    label.append(input);
    panel.append(label);
    inputs.push(input);
  }
  const reset = document.createElement('button');
  reset.type = 'button';
  reset.textContent = 'Сбросить';
  reset.addEventListener('click', () => settings.forEach(([, property, , , , value], i) => {
    inputs[i].value = value;
    document.documentElement.style.removeProperty(property);
  }));
  panel.append(reset);
  document.body.append(panel);
})();
