const boardEl=document.querySelector('#board'), statusEl=document.querySelector('#status');
const glyph={K:'♚',Q:'♛',R:'♜',B:'♝',N:'♞',P:'♟',k:'♚',q:'♛',r:'♜',b:'♝',n:'♞',p:'♟'};
let squares=Array(64).fill(null), selected=null, chosen='P', flipped=false, dragging=null;
const choices=['K','Q','R','B','N','P','k','q','r','b','n','p'];
function showPiece(element, piece) {
  if (!piece) return;
  element.textContent = glyph[piece];
  element.classList.add(piece === piece.toUpperCase() ? 'white-piece' : 'black-piece');
}

function render(){boardEl.innerHTML='';for(let vi=0;vi<64;vi++){let i=flipped?63-vi:vi, rank=7-Math.floor(i/8), file=i%8;const el=document.createElement('div');el.className='square '+((rank+file)%2?'light':'dark')+(selected===i?' selected':'');el.dataset.i=i;showPiece(el, squares[i]);el.draggable=!!squares[i];el.addEventListener('click',()=>clickSquare(i));el.addEventListener('dragstart',e=>{dragging=i;e.dataTransfer.setData('text/plain',String(i))});el.addEventListener('dragover',e=>e.preventDefault());el.addEventListener('drop',e=>{e.preventDefault();const from=Number(e.dataTransfer.getData('text/plain'));squares[i]=squares[from];squares[from]=null;selected=null;render()});boardEl.append(el)}}
function clickSquare(i){if(selected!==null){if(selected!==i){squares[i]=squares[selected];squares[selected]=null}selected=null}else if(squares[i])selected=i;else squares[i]=chosen;render()}
function fen(){let rows=[];for(let r=7;r>=0;r--){let row='',empty=0;for(let f=0;f<8;f++){const p=squares[r*8+f];if(!p)empty++;else{if(empty)row+=empty;empty=0;row+=p}}if(empty)row+=empty;rows.push(row)}return rows.join('/')+' w - - 0 1'}
function loadFen(value){squares=Array(64).fill(null);const placement=value.split(' ')[0];let r=7,f=0;for(const c of placement){if(c==='/'){r--;f=0}else if(/[1-8]/.test(c))f+=Number(c);else if(glyph[c])squares[r*8+f++]=c}render()}
const palette = document.querySelector('#palette');
const pieceNames = { K: 'king', Q: 'queen', R: 'rook', B: 'bishop', N: 'knight', P: 'pawn' };

for (const piece of choices) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'piece-choice';
  showPiece(button, piece);
  button.textContent += '\uFE0E';

  const side = piece === piece.toUpperCase() ? 'White' : 'Black';
  button.title = `${side} ${pieceNames[piece.toUpperCase()]}`;
  button.setAttribute('aria-label', button.title);
  button.setAttribute('aria-pressed', piece === chosen);
  button.onclick = () => {
    chosen = piece;
    palette.querySelector('[aria-pressed="true"]').setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-pressed', 'true');
  };
  palette.append(button);
}
render();
document.querySelector('#upload-form').addEventListener('submit',async e=>{e.preventDefault();const data=new FormData(e.currentTarget);statusEl.textContent='Reading file…';try{const res=await fetch('/api/recognize',{method:'POST',body:data}),body=await res.json();if(!res.ok)throw Error(body.detail||'Could not analyze file');loadFen(body.fen);statusEl.textContent=body.message}catch(err){statusEl.textContent=err.message}});
document.querySelector('#remove').onclick=()=>{if(selected!==null){squares[selected]=null;selected=null;render()}else statusEl.textContent='Select a piece on the board first.'};document.querySelector('#clear').onclick=()=>{squares=Array(64).fill(null);selected=null;render()};document.querySelector('#start').onclick=()=>loadFen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');document.querySelector('#flip').onclick=()=>{flipped=!flipped;render()};
document.querySelector('#save').onclick=async()=>{try{const res=await fetch('/api/positions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fen:fen()})}),body=await res.json();if(!res.ok)throw Error(body.detail);statusEl.textContent='Position saved.';loadPositions()}catch(err){statusEl.textContent='Could not save: '+err.message}};
async function loadPositions(){const res=await fetch('/api/positions');const items=await res.json();const ul=document.querySelector('#positions');ul.innerHTML='';items.forEach(item=>{const li=document.createElement('li');const a=document.createElement('a');a.href='#';a.textContent=item.fen;a.onclick=e=>{e.preventDefault();loadFen(item.fen)};li.append(a);ul.append(li)})}loadPositions();
