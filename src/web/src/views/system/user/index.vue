<template>
  <fs-page>
    <el-row class="mx-2">
      <el-col xs="24" :sm="8" :md="6" :lg="4" :xl="4" class="p-1">
        <el-card :body-style="{ height: '100%' }">
          <p class="user-tree-title">
            组织列表
            <el-tooltip effect="dark" :content="content" placement="right">
              <el-icon>
                <QuestionFilled/>
              </el-icon>
            </el-tooltip>
          </p>
          <el-input v-model="filterText" :placeholder="placeholder"/>
          <el-tree ref="treeRef" class="user-dept-tree" :data="data" :props="treeProps"
                   :filter-node-method="filterNode" icon="ArrowRightBold" :indent="38" highlight-current @node-click="onTreeNodeClick">
            <template #default="{ node, data }">
              <element-tree-line :node="node" :showLabelLine="false" :indent="32">
					<span v-if="data.status" class="user-tree-label">
						<SvgIcon name="iconfont icon-shouye" color="var(--el-color-primary)"/>&nbsp;{{ node.label }}
					</span>
                <span v-else color="var(--el-color-primary)"> <SvgIcon name="iconfont icon-shouye"/>&nbsp;{{
                    node.label
                  }} </span>
              </element-tree-line>
            </template>
          </el-tree>
        </el-card>
      </el-col>
      <el-col xs="24" :sm="16" :md="18" :lg="20" :xl="20" class="p-1">
        <el-card :body-style="{ height: '100%' }">
          <fs-crud ref="crudRef" v-bind="crudBinding">
<!--            <template #actionbar-right>-->
<!--              <importExcel api="api/system/user/" v-auth="'user:Import'">导入</importExcel>-->
<!--            </template>-->
            <template #cell_avatar="scope">
              <div v-if="scope.row.avatar" style="display: flex; justify-content: center; align-items: center;">
                <el-image 
                  style="width: 50px; height: 50px; border-radius: 50%; aspect-ratio: 1 /1 ; " 
                  :src="getBaseURL(scope.row.avatar)"
                  :preview-src-list="[getBaseURL(scope.row.avatar)]" 
                  :preview-teleported="true" />
              </div>
            </template>
          </fs-crud>
        </el-card>
      </el-col>
    </el-row>

  </fs-page>
</template>

<script lang="ts" setup name="user">
import {useExpose, useCrud} from '@fast-crud/fast-crud';
import {createCrudOptions} from './crud';
import * as api from './api';
import {ElTree} from 'element-plus';
import {ref, onMounted, watch, toRaw, h} from 'vue';
import XEUtils from 'xe-utils';
import {getElementLabelLine} from 'element-tree-line';
import importExcel from '/@/components/importExcel/index.vue'
import {getBaseURL} from '/@/utils/baseUrl';


const ElementTreeLine = getElementLabelLine(h);

interface Tree {
  id: number;
  name: string;
  status: boolean;
  children?: Tree[];
}

interface APIResponseData {
  code?: number;
  data: [];
  msg?: string;
}

// 引入组件
const placeholder = ref('请输入组织名称');
const filterText = ref('');
const treeRef = ref<InstanceType<typeof ElTree>>();

const treeProps = {
  children: 'children',
  label: 'name',
  icon: 'icon',
};

watch(filterText, (val) => {
  treeRef.value!.filter(val);
});

const filterNode = (value: string, data: Tree) => {
  if (!value) return true;
  return toRaw(data).name.indexOf(value) !== -1;
};

let data = ref([]);

const content = `
1.组织信息;
`;

const getData = () => {
  api.GetDept({}).then((ret: APIResponseData) => {
    const responseData = ret.data;
    const result = XEUtils.toArrayTree(responseData, {
      parentKey: 'parent',
      children: 'children',
    });

    data.value = result;
  });
};

//树形点击事件
const onTreeNodeClick = (node: any) => {
  const {id} = node;
  crudExpose.doSearch({form: {dept: id}});
};

// 页面打开后获取列表数据
onMounted(() => {
  getData();
});

// crud组件的ref
const crudRef = ref();
// crud 配置的ref
const crudBinding = ref();
// 暴露的方法
const {crudExpose} = useExpose({crudRef, crudBinding});
// 你的crud配置
const {crudOptions} = createCrudOptions({crudExpose});
// 初始化crud配置
const {resetCrudOptions} = useCrud({crudExpose, crudOptions});

// 页面打开后获取列表数据
onMounted(() => {
  crudExpose.doRefresh();
});
</script>

<style lang="scss" scoped>
.user-tree-title { font-size: var(--lims-type-card-title-size); font-weight: var(--lims-type-card-title-weight); color: var(--lims-text-primary); margin-bottom: var(--lims-space-4); }
.user-dept-tree { margin-top: var(--lims-space-3); font-size: var(--lims-type-form-value-size); font-weight: 400; overflow: auto; max-height: calc(100% - 80px); }
.user-dept-tree :deep(.el-tree-node__content) { min-height: 36px; }
.user-tree-label { font-family: inherit; font-weight: 400; }
.el-row {
  height: 100%;

  .el-col {
    height: 100%;
  }
}

.el-card {
  height: 100%;
}

.font-normal {
  font-family: Helvetica Neue, Helvetica, PingFang SC, Hiragino Sans GB, Microsoft YaHei, SimSun, sans-serif;
}
</style>
