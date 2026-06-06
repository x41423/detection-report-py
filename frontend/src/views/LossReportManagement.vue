<template>
  <div class="page-shell page">
    <PageHero title="报损报溢" subtitle="记录商品损耗和溢余，支持主子表明细。" />
    <el-card shadow="never" class="fcard">
      <div class="trow"><span class="snote">共 {{ items.length }} 条记录</span><el-button type="primary" size="small" @click="openCreate">新增报损报溢</el-button></div>
      <el-table :data="items" stripe size="small" style="margin-top:8px" @row-click="showDetail">
        <el-table-column prop="report_no" label="单号" width="150" />
        <el-table-column prop="report_date" label="日期" width="110" />
        <el-table-column label="类型" width="80"><template #default="{row}"><el-tag :type="row.report_type==='loss'?'danger':'warning'" size="small">{{row.report_type==='loss'?'报损':'报溢'}}</el-tag></template></el-table-column>
        <el-table-column label="金额" width="100"><template #default="{row}">¥{{ (row.total_amount||0).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="notes" label="备注" min-width="150" />
        <el-table-column label="状态" width="70"><template #default="{row}"><el-tag :type="row.status==='draft'?'info':'success'" size="small">{{row.status==='draft'?'草稿':'已确认'}}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="140"><template #default="{row}">
          <el-button link type="primary" size="small" @click.stop="showDetail(row)">明细</el-button>
          <el-popconfirm title="确定删除？" @confirm="del(row.id)"><template #reference><el-button link type="danger" size="small" @click.stop>删除</el-button></template></el-popconfirm>
        </template></el-table-column>
      </el-table>
    </el-card>
    <!-- create dialog -->
    <el-dialog v-model="dv" title="新增报损报溢" width="600px" @closed="rf">
      <el-form :model="f" label-width="80px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="日期"><el-input v-model="f.report_date" placeholder="2026-01-01" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="类型"><el-select v-model="f.report_type"><el-option label="报损" value="loss" /><el-option label="报溢" value="overflow" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="f.notes" type="textarea" :rows="2" /></el-form-item>
        <el-divider>明细</el-divider>
        <div v-for="(it,i) in f.items" :key="i" class="ilrow">
          <el-input-number v-model="it.product_id" :min="1" size="small" controls-position="right" style="width:80px" placeholder="商品ID" />
          <el-input-number v-model="it.quantity" :min="0" :step="1" size="small" controls-position="right" style="width:80px" placeholder="数量" />
          <el-input v-model="it.unit_name" size="small" style="width:60px" placeholder="单位" />
          <el-input-number v-model="it.unit_price" :min="0" :precision="2" size="small" controls-position="right" style="width:100px" placeholder="单价" />
          <span class="amt">¥{{ (it.quantity*it.unit_price).toFixed(2) }}</span>
          <el-input v-model="it.reason" size="small" style="flex:1;min-width:120px" placeholder="原因" />
          <el-button size="small" type="danger" link @click="f.items.splice(i,1)">×</el-button>
        </div>
        <el-button size="small" style="margin-top:8px" @click="f.items.push({product_id:0,quantity:0,unit_name:'',unit_price:0,amount:0,reason:''})">+ 添加明细</el-button>
      </el-form>
      <template #footer><el-button @click="dv=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
    <!-- detail dialog -->
    <el-dialog v-model="ddv" title="明细" width="600px">
      <p v-if="dr" class="dhdr">单号: {{dr.report_no}} | 日期: {{dr.report_date}} | 金额: ¥{{(dr.total_amount||0).toFixed(2)}}</p>
      <el-table :data="ditems" stripe size="small">
        <el-table-column prop="product_id" label="商品ID" width="80" />
        <el-table-column prop="quantity" label="数量" width="70" />
        <el-table-column prop="unit_name" label="单位" width="60" />
        <el-table-column label="单价" width="80"><template #default="{row}">¥{{ (row.unit_price||0).toFixed(2) }}</template></el-table-column>
        <el-table-column label="金额" width="80"><template #default="{row}">¥{{ (row.amount||0).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="reason" label="原因" min-width="120" />
      </el-table>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import {onMounted,reactive,ref} from 'vue';import {ElMessage} from 'element-plus';import PageHero from '../components/PageHero.vue'
import {getLossReports,getLossReport,createLossReport,deleteLossReport,type LossReport,type LossReportItem} from '../api/loss-report'
const items=ref<LossReport[]>([]);const dv=ref(false);const ddv=ref(false)
const dr=ref<LossReport|null>(null);const ditems=ref<LossReportItem[]>([])
interface ItemDraft {product_id:number;quantity:number;unit_name:string;unit_price:number;amount:number;reason:string}
const f=reactive<{report_date:string;report_type:string;notes:string;items:ItemDraft[]}>({report_date:'',report_type:'loss',notes:'',items:[]})
function rf(){f.report_date='';f.report_type='loss';f.notes='';f.items=[]}
function openCreate(){rf();dv.value=true}
async function save(){try{await createLossReport({...f,report_no:''});dv.value=false;ElMessage.success('已创建');await load()}catch(e:any){ElMessage.error(e?.response?.data?.detail||'保存失败')}}
async function del(id:number){await deleteLossReport(id);items.value=items.value.filter(i=>i.id!==id);ElMessage.success('已删除')}
async function showDetail(r:LossReport){try{const{data}=await getLossReport(r.id);dr.value=(data as any).report;ditems.value=(data as any).items;ddv.value=true}catch(e:any){ElMessage.error('加载明细失败')}}
async function load(){const{data}=await getLossReports();items.value=(data as any).items??[]}
onMounted(load)
</script>
<style scoped>
.fcard{margin-bottom:12px}.trow{display:flex;justify-content:space-between;align-items:center}.snote{color:var(--el-text-color-secondary);font-size:13px}
.ilrow{display:flex;align-items:center;gap:8px;margin-bottom:6px}.amt{color:var(--el-color-warning);font-weight:600;min-width:70px;font-size:13px}
.dhdr{margin:0 0 12px;color:var(--el-text-color-secondary);font-size:13px}
</style>
