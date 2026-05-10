
function app(){return{
  view:'chat',sidebarOpen:false,configOpen:false,openSelect:null,
  stats:{},rotationMode:'round_robin',rotCfg:{mode:'round_robin',cooldown:60},
  accounts:[],rotationAccounts:{},activeId:'',activeAccount:{},
  models:[],model:'',
  msgs:[],draft:'',selectedImages:[],busy:false,
  cfg:{thinking:'off',search:'off',stream:'on',temperature:1.0,topP:1.0,maxTokens:8192,safety:'on'},
  toast:{show:false,msg:'',t:null},
  cookieModal:{open:false,cookies:'',name:'',email:'',importing:false},

  init(){this.loadModels();this.loadStats();this.loadAccounts();this.loadRotation();document.addEventListener('click',()=>this.openSelect=null)},
  go(v){this.view=v;this.sidebarOpen=false;if(v==='dashboard')this.loadStats();if(v==='accounts'){this.loadAccounts();this.loadRotation()}},
  showToast(m){this.toast.msg=m;this.toast.show=true;if(this.toast.t)clearTimeout(this.toast.t);this.toast.t=setTimeout(()=>this.toast.show=false,3000)},
  toggleSelect(k,e){e.stopPropagation();this.openSelect=this.openSelect===k?null:k},
  selectOpt(k,model,val){this[model]=val;this.openSelect=null},
  renderMarkdown(text){
    if(!text) return '';
    if(typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined'){
      return DOMPurify.sanitize(marked.parse(text));
    }
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
  },

  async loadModels(){try{const r=await fetch('/v1/models');const d=await r.json();this.models=d.data||[];if(!this.model&&this.models.length)this.model=this.models[0].id}catch(e){}},
  async loadStats(){try{const r=await fetch('/stats');const d=await r.json();this.stats=d.models||{}}catch(e){}},
  async loadAccounts(){try{const[a,b]=await Promise.all([fetch('/accounts').then(r=>r.json()),fetch('/accounts/active').then(r=>r.json())]);this.accounts=a||[];this.activeId=b?.id||'';this.activeAccount=b||{}}catch(e){}},
  async loadRotation(){try{const r=await fetch('/rotation');const d=await r.json();this.rotationMode=d.mode||'round_robin';this.rotCfg.mode=d.mode||'round_robin';this.rotCfg.cooldown=d.cooldown_seconds||60;this.rotationAccounts=d.accounts||{}}catch(e){}},

  get accountRows(){return this.accounts.map(a=>({...a,...(this.rotationAccounts[a.id]||{})}))},
  get totalReqs(){return Object.values(this.stats).reduce((s,v)=>s+(v.requests||0),0)},
  get totalRL(){return Object.values(this.stats).reduce((s,v)=>s+(v.rate_limited||0),0)},

  async saveRotation(){try{await fetch('/rotation/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:this.rotCfg.mode,cooldown_seconds:this.rotCfg.cooldown})});this.showToast('已保存');this.loadRotation()}catch(e){this.showToast('保存失败')}},
  async forceNext(){try{await fetch('/rotation/next',{method:'POST'});this.showToast('已切换账号');this.loadAccounts()}catch(e){this.showToast('切换失败')}},
  async activateAccount(id){try{await fetch(`/accounts/${id}/activate`,{method:'POST'});this.showToast('已激活');this.loadAccounts();this.loadRotation()}catch(e){this.showToast('激活失败')}},
  async addAccount(){try{const r=await fetch('/accounts/login/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});this.showToast(r.ok?'登录已开始！':'启动登录失败')}catch(e){this.showToast('网络错误')}},
  async importCookies(){
    const raw=this.cookieModal.cookies.trim();
    if(!raw){this.showToast('请输入 Cookie');return}
    // 支持多行：每行一个 cookie 或用分号分隔
    const cookies=raw.split(/[\r\n]+/).map(l=>l.trim()).filter(Boolean).join('; ');
    this.cookieModal.importing=true;
    try{
      const body={cookies};
      if(this.cookieModal.name.trim()) body.name=this.cookieModal.name.trim();
      if(this.cookieModal.email.trim()) body.email=this.cookieModal.email.trim();
      const r=await fetch('/accounts/import-cookies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const d=await r.json();
      if(r.ok){
        this.showToast(`导入成功: ${d.cookie_count} 个 cookie`);
        this.cookieModal.open=false;this.cookieModal.cookies='';this.cookieModal.name='';this.cookieModal.email='';
        this.loadAccounts();this.loadRotation();
      }else{
        this.showToast(d.detail||'导入失败');
      }
    }catch(e){this.showToast('网络错误')}
    finally{this.cookieModal.importing=false}
  },

  resizeTa(){const el=this.$refs.ta;el.style.height='auto';el.style.height=Math.min(el.scrollHeight,200)+'px'},
  scrollDown(){setTimeout(()=>{const el=document.getElementById('chat-scroll');if(el)el.scrollTop=el.scrollHeight},50)},

  async handleImageUpload(e){
    const files=Array.from(e.target.files);
    for(const f of files){
      if(!f.type.startsWith('image/'))continue;
      const reader=new FileReader();
      reader.onload=(ev)=>this.selectedImages.push(ev.target.result);
      reader.readAsDataURL(f);
    }
    e.target.value='';
  },
  removeImage(idx){this.selectedImages.splice(idx,1)},

  async send(){const t=this.draft.trim();const imgs=[...this.selectedImages];if(!t && !imgs.length)return;if(this.busy||!this.model)return;
    this.msgs.push({role:'user',content:t,images:imgs});this.draft='';this.selectedImages=[];this.busy=true;this.resizeTa();this.scrollDown();

    // 生图模型走 /v1/images/generations
    if(this.model.includes('image')){
      try{const r=await fetch('/v1/images/generations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:this.model,prompt:t,size:'1024x1024'})});
        if(!r.ok){let e=r.statusText;try{const d=await r.json();if(d.detail)e=JSON.stringify(d.detail)}catch(x){};this.msgs.push({role:'assistant',content:'',error:`Error ${r.status}: ${e}`})}
        else{const d=await r.json();const imgs=d.data||[];let content='';imgs.forEach(img=>{if(img.b64_json)content+=`![image](data:image/png;base64,${img.b64_json})\n`;else if(img.url)content+=`![image](${img.url})\n`;if(img.revised_prompt)content+=img.revised_prompt+'\n'});
          this.msgs.push({role:'assistant',content:content||'(无响应内容)',showThinking:false})}}
      catch(e){this.msgs.push({role:'assistant',content:'',error:e.message})}
      finally{this.busy=false;this.scrollDown()}
      return;
    }

    const messages=this.msgs.map(m=>{
      if(m.images && m.images.length){
        const parts=[{type:'text',text:m.content||''}];
        m.images.forEach(img=>parts.push({type:'image_url',image_url:{url:img}}));
        return {role:m.role,content:parts};
      }
      return {role:m.role,content:m.content};
    });

    const body={model:this.model,messages};
    if(this.cfg.temperature!==1) body.temperature=this.cfg.temperature;
    if(this.cfg.topP!==1) body.top_p=this.cfg.topP;
    if(this.cfg.maxTokens!==8192) body.max_tokens=this.cfg.maxTokens;
    if(this.cfg.stream==='on') body.stream=true;
    if(this.cfg.thinking!=='off') body.thinking=this.cfg.thinking;
    if(this.cfg.search==='on') body.grounding=true;
    if(this.cfg.safety==='off') body.safety_off=true;

    try{const r=await fetch('/v1/chat/completions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if(!r.ok){let e=r.statusText;try{const d=await r.json();if(d.detail)e=JSON.stringify(d.detail)}catch(x){};this.msgs.push({role:'assistant',content:'',error:`Error ${r.status}: ${e}`})}
      else if(this.cfg.stream==='on'){
        const reader=r.body.getReader();const dec=new TextDecoder();this.msgs.push({role:'assistant',content:'',thinking:'',showThinking:false});const idx=this.msgs.length-1;let buf='';
        while(true){const{done,value}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});const lines=buf.split('\n');buf=lines.pop();
          for(const ln of lines){if(ln.startsWith('data: ')&&ln!=='data: [DONE]'){try{const d=JSON.parse(ln.slice(6));const delta=d.choices?.[0]?.delta||{};
            const c=delta.content;if(c)this.msgs[idx].content+=c;
            const th=delta.reasoning_content||delta.thinking||delta.reasoning;if(th)this.msgs[idx].thinking+=th;
          }catch(e){}}}
          this.scrollDown()}
      }else{const d=await r.json();const msg=d.choices?.[0]?.message||{};
        this.msgs.push({role:'assistant',content:msg.content||'(无响应内容)',thinking:msg.reasoning_content||msg.thinking||msg.reasoning||'',showThinking:false})}}
    catch(e){this.msgs.push({role:'assistant',content:'',error:e.message})}
    finally{this.busy=false;this.scrollDown()}},

  fmtDate(s){if(!s)return'-';try{return new Date(s).toLocaleString()}catch(e){return s}}
}}
