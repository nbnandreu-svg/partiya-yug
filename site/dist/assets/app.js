"use strict";
document.documentElement.classList.add('js');
const siteData = JSON.parse(document.getElementById('site-data').textContent);
const menu = document.querySelector('.menu-toggle');
const nav = document.getElementById('main-nav');
menu?.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  menu.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
  nav.classList.toggle('open', open);
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && nav.classList.contains('open')) {
    nav.classList.remove('open'); menu.setAttribute('aria-expanded','false'); menu.setAttribute('aria-label','Открыть меню'); menu.focus();
  }
});
const money = n => new Intl.NumberFormat('ru-RU', {maximumFractionDigits:2}).format(n).replace(/[\u00a0\u202f]/g,' ') + ' ₽';
const calc = document.getElementById('calc-form');
if (calc) {
  const q = document.getElementById('calc-quantity');
  const boxes = document.getElementById('calc-boxes');
  const volume = document.getElementById('calc-volume');
  const days = document.getElementById('calc-days');
  const error = document.getElementById('calc-error');
  const rates = siteData.rates;
  const fields = [q, boxes, volume, days];
  const update = () => {
    const mode = calc.elements.mode.value;
    const active = mode === 'fbs' ? [q,volume,days] : fields;
    if (active.some(x => !x.value.trim() || !x.checkValidity() || !Number.isFinite(x.valueAsNumber))) {
      error.textContent = 'Укажите допустимые неотрицательные значения. Количество должно быть целым и больше нуля.';
      document.getElementById('calc-total').textContent = 'Проверьте данные';
      document.getElementById('calc-lines').replaceChildren(); return;
    }
    error.textContent = '';
    const n=q.valueAsNumber;
    const lines = [
      [mode==='fbs'?'Сборка заказов':'Приемка и пересчет',n*(mode==='fbs'?rates.fbsPick:rates.receive)],
      ['Этикетки',n*rates.label],['Упаковочная операция',n*rates.pack],['Пакеты',n*rates.material],
      ['Хранение',volume.valueAsNumber*days.valueAsNumber*rates.storageM3Day]
    ];
    if(mode==='fbo') lines.push(['Доставка коробов',boxes.valueAsNumber*rates.boxDelivery]);
    const target=document.getElementById('calc-lines'); target.replaceChildren();
    lines.forEach(([label,value]) => {const row=document.createElement('div'),name=document.createElement('span'),amount=document.createElement('strong'); name.textContent=label;amount.textContent=money(value);row.append(name,amount);target.append(row);});
    document.getElementById('calc-total').textContent=money(lines.reduce((sum,l)=>sum+l[1],0));
  };
  const modeChange = () => {
    const isFbs=calc.elements.mode.value==='fbs';
    document.getElementById('quantity-label').textContent=isFbs?'Заказов в месяц, шт.':'Товаров в партии, шт.';
    document.getElementById('boxes-field').hidden=isFbs;boxes.disabled=isFbs;
    q.value=isFbs?siteData.defaults.orders:siteData.defaults.units;
    volume.value=isFbs?siteData.defaults.volume:0; days.value=isFbs?siteData.defaults.days:0;
    document.getElementById('calc-condition').textContent=isFbs?'Один товар, один пакет и одна этикетка в каждом заказе. Пример за выбранное число дней без специальных операций.':'Один товар в индивидуальном пакете и одна этикетка на единицу. Типовой пример без специальных операций.';
    document.getElementById('calc-exclusions').textContent=isFbs?'Не включены приемка запаса, доставка заказов, возвраты и специальные операции. Налоговые условия уточняются при согласовании цены.':'Не включены забор у поставщика и нестандартные работы. Хранение учитывается по введенным объему и сроку. Налоговые условия уточняются при согласовании цены.';
    update();
  };
  calc.addEventListener('input',update);
  calc.querySelectorAll('input[name="mode"]').forEach(r=>r.addEventListener('change',modeChange));
  calc.addEventListener('submit',event=>event.preventDefault());
  if(new URLSearchParams(location.search).get('mode')==='fbs') {calc.querySelector('[value="fbs"]').checked=true;modeChange();} else update();
}
document.querySelectorAll('.lead-form').forEach(form=>form.addEventListener('submit',event=>{
  event.preventDefault(); const output=form.querySelector('.form-result');
  if(!form.checkValidity() || !form.elements.product.value.trim()) {output.textContent='Укажите товар и целое количество от 1 до 1 000 000.';form.reportValidity();return;}
  const product=form.elements.product.value.trim();
  output.textContent=`Пример заявки: ${product}, ${form.elements.quantity.value} шт. Заявка не отправлена. Для запуска сайта нужно подключить прием обращений.`;
}));
document.querySelectorAll('.lead-form button[type="submit"]').forEach(button=>{button.disabled=false;});
