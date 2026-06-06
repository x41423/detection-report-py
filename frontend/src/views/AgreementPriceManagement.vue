<template>
  <div class="page-shell page">
    <PageHero title="协议价管理" subtitle="供应商协议价格维护，入库时可按协议价自动填入。" />
    <el-card shadow="never" class="fcard">
      <div class="trow"><span class="snote">共 {{ items.length }} 条协议</span><el-button type="primary" size="small" @click="openCreate">新增协议</el-button></div>
      <el-table :data="items" stripe size="small" style="margin-top:8px">
        <el-table-column prop="supplier_id" label="供应商" width="100" />
        <el-table-column prop="product_id" label="商品" width="100" />
        <el-table-column prop="price" label="协议单价" width="100"><template #default="{row}">¥{{ row.price.toFixed(2) }}</template></el-table-column>
        <el-table-column prop="unit_name" label="单位" width="70" />
        <el-table-column label="有效期" width="180"><template #default="{row}">{{row.effective_from||'—'}} ~ {{row.effective_to||'—'}}</template></el-table-column>
        <el-table-column label="状态" width="70"><template #default="{row}"><el-tag :type="row.is_active?'success':'info'" size="small">{{row.is_active?'启用':'停用'}}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="140"><template #default="{row}">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="del(row.id)"><template #reference><el-button link type="danger" size="small">删除</el-button></template></el-popconfirm>
        </template></el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dv" :title="eid?'编辑':'新增'" width="440px" @closed="rf">
      <el-form :model="f" label-width="80px">
        <el-form-item label="供应商"><el-input-number v-model="f.supplier_id" :min="1" controls-position="right" /></el-form-item>
        <el-form-item label="商品"><el-input-number v-model="f.product_id" :min="1" controls-position="right" /></el-form-item>
        <el-form-item label="协议单价"><el-input-number v-model="f.price" :min="0" :precision="2" :step="0.1" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="f.unit_name" placeholder="斤/公斤/件" /></el-form-item>
        <el-form-item label="生效日期"><el-input v-model="f.effective_from" placeholder="2026-01-01" /></el-form-item>
        <el-form-item label="失效日期"><el-input v-model="f.effective_to" placeholder="2026-12-31" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="f.is_active" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dv=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import {onMounted,reactive,ref} from 'vue';import {ElMessage} from 'element-plus';import PageHero from '../components/PageHero.vue'
import {getAgreements,createAgreement,updateAgreement,deleteAgreement,type AgreementPrice} from '../api/agreement-price'
const items=ref<AgreementPrice[]>([]);const dv=ref(false);const eid=ref<number|null>(null)
const f=reactive({supplier_id:0,product_id:0,price:0,unit_name:'',effective_from:'',effective_to:'',is_active:1})
function rf(){eid.value=null;f.supplier_id=0;f.product_id=0;f.price=0;f.unit_name='';f.effective_from='';f.effective_to='';f.is_active=1}
function openCreate(){rf();dv.value=true}
function openEdit(r:AgreementPrice){eid.value=r.id;f.supplier_id=r.supplier_id;f.product_id=r.product_id;f.price=r.price;f.unit_name=r.unit_name;f.effective_from=r.effective_from;f.effective_to=r.effective_to;f.is_active=r.is_active;dv.value=true}
async function save(){try{const d={...f,is_active:f.is_active}
eid.value?await updateAgreement(eid.value,d):await createAgreement(d);dv.value=false;ElMessage.success('已保存');await load()}catch(e:any){ElMessage.error(e?.response?.data?.detail||'保存失败')}}
async function del(id:number){await deleteAgreement(id);items.value=items.value.filter(i=>i.id!==id);ElMessage.success('已删除')}
async function load(){const{data}=await getAgreements();items.value=(data as any).items??[]}
onMounted(load)
</script>
<style scoped>.fcard{margin-bottom:12px}.trow{display:flex;justify-content:space-between;align-items:center}.snote{color:var(--el-text-color-secondary);font-size:13px}</style>
