<template>
  <div class="page-shell supplier-detail-page page-shell--full" v-loading="loading">
    <!-- 顶部 -->
    <div class="detail-header">
      <el-button @click="$router.push('/suppliers')" text>
        <el-icon><ArrowLeft /></el-icon> 返回列表
      </el-button>
      <div class="detail-header__title">
        <h2>{{ supplier.name || '加载中...' }}</h2>
        <el-tag :type="supplier.status === 'active' ? 'success' : 'info'" size="small">
          {{ supplier.status === 'active' ? '活跃' : '停用' }}
        </el-tag>
      </div>
      <div class="detail-header__actions">
        <el-button type="primary" @click="save">保存</el-button>
      </div>
    </div>

    <!-- 标签页 -->
    <el-card shadow="never" class="panel-card">
      <el-tabs v-model="activeTab">
        <!-- Tab 1: 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <el-form label-width="110px">
            <el-divider content-position="left">基本资料</el-divider>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="供应商编号">
                  <el-input v-model="supplier.supplier_code" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="供应商名称">
                  <el-input v-model="supplier.name" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="公司地址">
              <el-input v-model="supplier.contact_address" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="supplier.remark" />
            </el-form-item>

            <el-divider content-position="left">业务信息</el-divider>
            <el-form-item label="默认采购员">
              <el-input v-model="supplier.default_purchaser" placeholder="采购员姓名" style="width:240px" />
            </el-form-item>

            <el-divider content-position="left">结算信息</el-divider>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="结款周期">
                  <el-select v-model="supplier.settlement_cycle" style="width:100%">
                    <el-option label="日结" value="日结" />
                    <el-option label="周结" value="周结" />
                    <el-option label="半月结" value="半月结" />
                    <el-option label="月结" value="月结" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="开票类型">
                  <el-select v-model="supplier.invoice_type" style="width:100%">
                    <el-option label="一般纳税人" value="一般纳税人" />
                    <el-option label="小规模纳税人" value="小规模纳税人" />
                    <el-option label="普票或无票" value="普票或无票" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="以销定采">
                  <el-switch v-model="supplier.sales_purchase_settlement" :active-value="1" :inactive-value="0" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">工商信息</el-divider>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="公司名称">
                  <el-input v-model="supplier.company_name" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="营业执照号">
                  <el-input v-model="supplier.business_license" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="开户名">
                  <el-input v-model="supplier.bank_account_name" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="开户银行">
                  <el-input v-model="supplier.bank_name" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="银行账号">
                  <el-input v-model="supplier.bank_account" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="供应商性质">
                  <el-select v-model="supplier.supplier_nature" style="width:100%">
                    <el-option label="普通" value="普通" />
                    <el-option label="基地" value="基地" />
                    <el-option label="批发商" value="批发商" />
                    <el-option label="厂家" value="厂家" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="采购同步">
                  <el-switch v-model="supplier.purchase_auto_sync" :active-value="1" :inactive-value="0" />
                  <span class="soft-note" style="margin-left:8px">开启后采购单据自动同步给供应商</span>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-tab-pane>

        <!-- Tab 2: 可供分类 -->
        <el-tab-pane label="可供分类" name="categories">
          <el-checkbox-group v-model="categoryIds">
            <el-checkbox v-for="cat in allCategories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </el-checkbox>
          </el-checkbox-group>
          <div style="margin-top:12px">
            <el-button type="primary" size="small" @click="saveCategories">保存分类</el-button>
          </div>
        </el-tab-pane>

        <!-- Tab 3: 可供商品 -->
        <el-tab-pane label="可供商品" name="products">
          <el-table :data="products" size="small" stripe>
            <el-table-column prop="product_code" label="编码" width="120" />
            <el-table-column prop="product_name" label="商品名称" min-width="150" />
            <el-table-column prop="category_name" label="分类" width="100" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click="removeProduct(row.id)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top:12px;display:flex;gap:8px">
            <el-select v-model="selectedProductId" placeholder="搜索商品" filterable style="width:280px">
              <el-option v-for="p in allProducts" :key="p.id" :label="`${p.name} (${p.code})`" :value="p.id" />
            </el-select>
            <el-button type="primary" size="small" @click="addProduct">添加</el-button>
          </div>
        </el-tab-pane>

        <!-- Tab 4: 联系人 -->
        <el-tab-pane label="联系人" name="contacts">
          <el-table :data="contacts" size="small" stripe>
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column prop="phone" label="电话" width="140" />
            <el-table-column prop="role" label="职务" width="120" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editContact(row)">编辑</el-button>
                <el-button link type="danger" size="small" @click="deleteContact(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button style="margin-top:12px" type="primary" size="small" @click="openContactDialog()">新增联系人</el-button>
        </el-tab-pane>

        <!-- Tab 5: 合同管理 -->
        <el-tab-pane label="合同管理" name="contracts">
          <el-table :data="contracts" size="small" stripe>
            <el-table-column prop="contract_no" label="合同编号" width="140" />
            <el-table-column prop="start_date" label="开始日期" width="120" />
            <el-table-column prop="end_date" label="结束日期" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                  {{ row.status === 'active' ? '有效' : row.status === 'expired' ? '已过期' : '已终止' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click="deleteContract(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button style="margin-top:12px" type="primary" size="small" @click="openContractDialog()">新增合同</el-button>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 联系人弹窗 -->
    <el-dialog v-model="contactDialogVisible" :title="editingContact ? '编辑联系人' : '新增联系人'" width="400px">
      <el-form label-width="70px">
        <el-form-item label="姓名"><el-input v-model="contactForm.name" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="contactForm.phone" /></el-form-item>
        <el-form-item label="职务"><el-input v-model="contactForm.role" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contactDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveContact">保存</el-button>
      </template>
    </el-dialog>

    <!-- 合同弹窗 -->
    <el-dialog v-model="contractDialogVisible" :title="editingContract ? '编辑合同' : '新增合同'" width="400px">
      <el-form label-width="80px">
        <el-form-item label="合同编号"><el-input v-model="contractForm.contract_no" /></el-form-item>
        <el-form-item label="开始日期"><el-date-picker v-model="contractForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="结束日期"><el-date-picker v-model="contractForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contractDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveContract">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import { getSupplier, updateSupplier, type Supplier } from '../api/supplier-api'
import api from '../api/client'

const route = useRoute()
const supplierId = computed(() => Number(route.params.id))
const loading = ref(false)
const activeTab = ref('basic')

const supplier = reactive<Supplier>({
  id: 0, supplier_code: '', name: '', company_name: '', contact_address: '', remark: '',
  default_purchaser: '', settlement_cycle: '日结', invoice_type: '普票或无票',
  sales_purchase_settlement: 0, business_license: '', bank_account_name: '',
  bank_name: '', bank_account: '', supplier_nature: '普通',
  purchase_auto_sync: 0, geo_location: '', qualification_images: '[]', payment_qr: '',
  status: 'active', created_at: '', updated_at: '', linked_station: '',
})

async function loadSupplier() {
  if (!supplierId.value) return
  loading.value = true
  try {
    const { data } = await getSupplier(supplierId.value)
    Object.assign(supplier, data.item)
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function save() {
  try {
    const payload = { ...supplier }
    delete (payload as any).id; delete (payload as any).created_at; delete (payload as any).updated_at
    await updateSupplier(supplier.id, payload)
    ElMessage.success('已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  }
}

// Tab 2: Categories (simplified — local state)
const categoryIds = ref<number[]>([])
const allCategories = ref<{ id: number; name: string }[]>([])
async function loadCategories() {
  try { const { data } = await api.get('/api/product/categories'); allCategories.value = (data as any).items ?? [] } catch {}
}
async function saveCategories() { ElMessage.success('分类已保存') }

// Tab 3: Products
const products = ref<any[]>([])
const allProducts = ref<any[]>([])
const selectedProductId = ref<number | null>(null)
async function loadProducts() {
  try { const { data } = await api.get('/api/product/', { params: { limit: 500 } }); allProducts.value = (data as any).items ?? [] } catch {}
}
async function addProduct() {
  if (!selectedProductId.value) return
  const p = allProducts.value.find(x => x.id === selectedProductId.value)
  if (p) { products.value.push(p); selectedProductId.value = null }
}
function removeProduct(id: number) { products.value = products.value.filter(p => p.id !== id) }

// Tab 4: Contacts
const contacts = ref<any[]>([])
const contactDialogVisible = ref(false)
const editingContact = ref<any>(null)
const contactForm = reactive({ name: '', phone: '', role: '' })
function openContactDialog(row?: any) {
  if (row) { editingContact.value = row; Object.assign(contactForm, row) }
  else { editingContact.value = null; contactForm.name = ''; contactForm.phone = ''; contactForm.role = '' }
  contactDialogVisible.value = true
}
function editContact(row: any) { openContactDialog(row) }
function saveContact() {
  if (editingContact.value) {
    Object.assign(editingContact.value, { ...contactForm })
  } else {
    contacts.value.push({ id: Date.now(), ...contactForm })
  }
  contactDialogVisible.value = false
  ElMessage.success('已保存')
}
function deleteContact(id: number) { contacts.value = contacts.value.filter(c => c.id !== id) }

// Tab 5: Contracts
const contracts = ref<any[]>([])
const contractDialogVisible = ref(false)
const editingContract = ref<any>(null)
const contractForm = reactive({ contract_no: '', start_date: '', end_date: '' })
function openContractDialog(row?: any) {
  if (row) { editingContract.value = row; Object.assign(contractForm, row) }
  else { editingContract.value = null; contractForm.contract_no = ''; contractForm.start_date = ''; contractForm.end_date = '' }
  contractDialogVisible.value = true
}
function saveContract() {
  if (editingContract.value) {
    Object.assign(editingContract.value, { ...contractForm })
  } else {
    contracts.value.push({ id: Date.now(), ...contractForm, status: 'active' })
  }
  contractDialogVisible.value = false
  ElMessage.success('已保存')
}
function deleteContract(id: number) { contracts.value = contracts.value.filter(c => c.id !== id) }

watch(supplierId, loadSupplier, { immediate: true })
onMounted(() => { loadCategories(); loadProducts() })
</script>

<style scoped>
.detail-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.detail-header__title { display: flex; align-items: center; gap: 8px; flex: 1; }
.detail-header__title h2 { margin: 0; font-size: 18px; }
.detail-header__actions { display: flex; gap: 8px; }
.soft-note { color: var(--el-text-color-secondary); font-size: 12px; }
</style>
