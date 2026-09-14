<template>
	<fs-page class="PageFeatureSearchMulti">
		<fs-crud ref="crudRef" v-bind="crudBinding">
			<template #cell_url="scope">
				<el-tag size="small">{{ scope.row.url }}</el-tag>
			</template>
			<!--  功能说明:使用导入组件，并且修改api地址为当前对应的api，当前是demo的api="api/CarModelViewSet/"-->
			<template #actionbar-right>
				<importExcel api="api/VIEWSETNAME/" v-auth="'user:Import'">导入</importExcel>
			</template>
		</fs-crud>
	</fs-page>
</template>

<script lang="ts">
import { onMounted, getCurrentInstance, defineComponent} from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import createCrudOptions  from './crud';

// 导入组件
import importExcel from '/@/components/importExcel/index.vue'


export default defineComponent({    //这里配置defineComponent
    name: "VIEWSETNAME",   //把name放在这里进行配置了
	components: {importExcel},  //注册组件，把importExcel组件放在这里，这样<template></template>中才能正确的引用到组件
    setup() {   //这里配置了setup()

		const instance = getCurrentInstance();

		const context: any = {
			componentName: instance?.type.name
		};

		const { crudBinding, crudRef, crudExpose, resetCrudOptions } = useFs({ createCrudOptions, context});


		// 页面打开后获取列表数据
		onMounted(() => {
			crudExpose.doRefresh();
		});
		return {
		//增加了return把需要给上面<template>内调用的<fs-crud ref="crudRef" v-bind="crudBinding">
				crudBinding,
				crudRef,
			};


    } 	//这里关闭setup()
  });  //关闭defineComponent

</script>
