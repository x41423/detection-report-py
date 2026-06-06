<template>
  <div class="page-shell page page-shell--full">
    <PageHero title="改单审核" subtitle="订单修改提交审核，审核通过后生效。" />
    <el-card shadow="never" class="fcard">
      <div class="trow">
        <el-radio-group v-model="filterStatus" size="small" @change="load">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="pending">待审核</el-radio-button>
          <el-radio-button value="approved">已通过</el-radio-button>
          <el-radio-button value="rejected">已驳回</el-radio-button>
        </el-radio-group>
        <el-button type="primary" size="small" @click="openCreate">新增改单</el-button>
      </div>
      <el-table :data="items" stripe size="small" style="margin-top:8px">
        <el-table-column prop="order_no" label="订单号" width="160" />
        <el-table-column prop="order_id" label="订单ID" width="70" />
        <el-table-column prop="modifier_name" label="申请人" width="90" />
        <el-table-column prop="summary" label="变更摘要" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="80"><template #default="{row}">
          <el-tag :type="row.status==='pending'?'warning':row.status==='approved'?'success':'danger'" size="small">
            {{row.status==='pending'?'待审':row.status==='approved'?'通过':'驳回'}}
          </el-tag></template></el-table-column>
        <el-table-column prop="reviewer_name" label="审核人" width="80" />
        <el-table-column prop="review_comment" label="审核意见" min-width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="160" v-if="filterStatus==='pending'||!filterStatus"><template #default="{row}">
          <template v-if="row.status==='pending'">
            <el-button link type="success" size="small" @click="approve(row)">通过</el-button>
            <el-button link type="danger" size="small" @click="reject(row)">驳回</el-button>
          </template>
          <span v-else class="snote">—</span>
        </template></el-table-column>
      </el-table>
    </el-card>
    <!-- Create dialog -->
    <el-dialog v-model="dv" title="提交改单" width="440px" @closed="rf">
      <el-form :model="f" label-width="80px">
        <el-form-item label="订单ID"><el-input-number v-model="f.order_id" :min="1" /></el-form-item>
        <el-form-item label="订单号"><el-input v-model="f.order_no" placeholder="可选" /></el-form-item>
        <el-form-item label="申请人"><el-input v-model="f.modifier_name" /></el-form-item>
        <el-form-item label="变更说明"><el-input v-model="f.summary" type="textarea" :rows="3" placeholder="描述修改了哪些内容" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dv=false">取消</el-button><el-button type="primary" @click="save">提交审核</el-button></template>
    </el-dialog>
    <!-- Approve/Reject confirm -->
    <el-dialog v-model="av" title="审核意见" width="360px">
      <el-input v-model="reviewComment" type="textarea" :rows="2" placeholder="审核意见（可选）" />
      <template #footer><el-button @click="av=false">取消</el-button><el-button type="primary" @click="confirmAction">确认</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import {onMounted,reactive,ref} from 'vue';import {ElMessage} from 'element-plus';import PageHero from '../components/PageHero.vue'
import {getModifications,createModification,approveModification,rejectModification,type OrderModification} from '../api/order-modification'
const items=ref<OrderModification[]>([]);const filterStatus=ref('');const dv=ref(false);const av=ref(false)
const f=reactive({order_id:0,order_no:'',modifier_name:'',summary:''})
let pendingAction:'approve'|'reject'='approve';let pendingId=0;const reviewComment=ref('')
function rf(){f.order_id=0;f.order_no='';f.modifier_name='';f.summary=''}
function openCreate(){rf();dv.value=true}
async function save(){try{await createModification({...f});dv.value=false;ElMessage.success('已提交');await load()}catch(e:any){ElMessage.error(e?.response?.data?.detail||'提交失败')}}
function approve(r:OrderModification){pendingId=r.id;pendingAction='approve';reviewComment.value='';av.value=true}
function reject(r:OrderModification){pendingId=r.id;pendingAction='reject';reviewComment.value='';av.value=true}
async function confirmAction(){try{
pendingAction==='approve'?await approveModification(pendingId,'管理员',reviewComment.value):await rejectModification(pendingId,'管理员',reviewComment.value)
av.value=false;ElMessage.success(pendingAction==='approve'?'已通过':'已驳回');await load()}catch(e:any){ElMessage.error('操作失败')}}
async function load(){const{data}=await getModifications({status:filterStatus.value||undefined});items.value=(data as any).items??[]}
onMounted(load)
</script>
<style scoped>.fcard{margin-bottom:12px}.trow{display:flex;justify-content:space-between;align-items:center}.snote{color:var(--el-text-color-secondary);font-size:13px}</style>
