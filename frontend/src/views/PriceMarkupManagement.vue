<template>
  <div class="page-shell page">
    <PageHero title="上浮定价" subtitle="设置商品价格上浮比例，支持全局、按分类或按商品。" />
    <el-card shadow="never" class="fcard">
      <div class="trow"><span class="snote">共 {{ items.length }} 条规则</span><el-button type="primary" size="small" @click="openCreate">新增规则</el-button></div>
      <el-table :data="items" stripe size="small" style="margin-top:8px">
        <el-table-column prop="name" label="规则名称" min-width="150" />
        <el-table-column label="上浮比例" width="120"><template #default="{row}">{{ (row.rate*100).toFixed(0) }}%</template></el-table-column>
        <el-table-column prop="scope" label="范围" width="100"><template #default="{row}"><el-tag size="small">{{scopeLabel(row.scope)}}</el-tag></template></el-table-column>
        <el-table-column label="状态" width="80"><template #default="{row}"><el-tag :type="row.is_active?'success':'info'" size="small">{{row.is_active?'启用':'停用'}}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="140"><template #default="{row}">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="del(row.id)"><template #reference><el-button link type="danger" size="small">删除</el-button></template></el-popconfirm>
        </template></el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dv" :title="eid?'编辑':'新增'" width="420px" @closed="rf">
      <el-form :model="f" label-width="80px">
        <el-form-item label="名称"><el-input v-model="f.name" /></el-form-item>
        <el-form-item label="上浮比例(%)"><el-input-number v-model="f.ratePct" :min="0" :max="500" :step="1" /></el-form-item>
        <el-form-item label="范围"><el-select v-model="f.scope"><el-option label="全局" value="global" /><el-option label="分类" value="category" /><el-option label="商品" value="product" /></el-select></el-form-item>
        <el-form-item label="启用"><el-switch v-model="f.is_active" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dv=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import {onMounted,reactive,ref} from 'vue';import {ElMessage} from 'element-plus';import PageHero from '../components/PageHero.vue'
import {getMarkups,createMarkup,updateMarkup,deleteMarkup,type PriceMarkup} from '../api/price-markup'
const items=ref<PriceMarkup[]>([]);const dv=ref(false);const eid=ref<number|null>(null)
const f=reactive({name:'',ratePct:10,scope:'global',is_active:1})
function scopeLabel(s:string){return s==='global'?'全局':s==='category'?'分类':'商品'}
function rf(){eid.value=null;f.name='';f.ratePct=10;f.scope='global';f.is_active=1}
function openCreate(){rf();dv.value=true}
function openEdit(r:PriceMarkup){eid.value=r.id;f.name=r.name;f.ratePct=Math.round(r.rate*100);f.scope=r.scope;f.is_active=r.is_active;dv.value=true}
async function save(){try{const d={name:f.name,rate:f.ratePct/100,scope:f.scope,scope_id:0,is_active:f.is_active}
eid.value?await updateMarkup(eid.value,d):await createMarkup(d);dv.value=false;ElMessage.success('已保存');await load()}catch(e:any){ElMessage.error(e?.response?.data?.detail||'保存失败')}}
async function del(id:number){await deleteMarkup(id);items.value=items.value.filter(i=>i.id!==id);ElMessage.success('已删除')}
async function load(){const{data}=await getMarkups();items.value=(data as any).items??[]}
onMounted(load)
</script>
<style scoped>.fcard{margin-bottom:12px}.trow{display:flex;justify-content:space-between;align-items:center}.snote{color:var(--el-text-color-secondary);font-size:13px}</style>
